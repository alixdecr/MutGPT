import random, re, ast
from utils.makeRequest import makeLLMRequest
from utils.requestFormat import requestToDict, dictToRequest


class RequestMutation:


    def __init__(self):

        # Give me all possible parameter names and values that can replace the <op>=<op> token placeholder as strings of the structure 'param=value', with example values for each parameter.

        self.mutationOperators = {
            "addRoute": {"description": "The <op> token is masking a route of the request. Give me all possible routes that can replace the <op> token placeholder."},
            "removeRoute": {"description": "Remove an existing route."},
            "modifyRoute": {"description": "The <op> token is masking a route of the request. Give me all possible routes that can replace the <op> token placeholder."},
            "addParameter": {"description": "The <op>=<op> token is masking a parameter name and value. Give me all possible parameter names and values that can replace the <op>=<op> token placeholder. The given answers need to be strings of the structure 'param=value'."},
            "removeParameter": {"description": "Remove an existing parameter name and value"},
            "modifyParameter": {"description": "The <op>=<op> token is masking a parameter name and value. Give me all possible parameter names and values that can replace the <op>=<op> token placeholder. The given answers need to be strings of the structure 'param=value', with example values for each parameter."},
            "modifyParameterName": {"description": "The <op> token is masking a parameter name. Give me all possible parameter names that can replace the <op> token placeholder."},
            "modifyParameterValue": {"description": "The <op> token is masking a parameter value. Give me all possible parameter values that can replace the <op> token placeholder."},
            "resetParameters": {"description": "The <op>=<op> token is masking a parameter name and value. Give me all possible parameter names and values that can replace the <op>=<op> token placeholder. The given answers need to be strings of the structure 'param=value'."}
        }


    def applyMutationStrategy(self, strategy, request, nbBaseRoutes, name, model, randomness, openaiKey, apiKey):

        # find adequate mutation operator based on the request
        mutationOperator = self.findMutationOperator(request, nbBaseRoutes)

        # mask the request with the mutation operator
        maskedRequest = self.maskRequest(request, mutationOperator)

        maskValues = []
        mutatedRequests = []

        # if remove operator, no need to send to LLM and the mutated request = masked request
        if mutationOperator in ["removeRoute", "removeParameter"]:
            mutatedRequests = [maskedRequest]

        else:

            if strategy == "allMaskValues":

                # ask LLM for all possible values to replace the mask
                #prompt = f"Give me a Python list only containing all possible and valid values that can replace the <op> token mask in the following request: {maskedRequest}. {self.mutationOperators[mutationOperator]['description']}. Make sure that each value given is valid for the {name}, do NOT invent any routes and parameters, only use real ones that exist in the API. Also make sure that your answer is a Python list of the following structure: ['element1', 'element2', ...]."

                # UPDATED PROMPT: COMMENT THIS LINE AND UNCOMMENT PREVIOUS LINE FOR PREVIOUS PROMPT
                prompt = self.generatePrompt(mutationOperator, maskedRequest, name)

                response = makeLLMRequest(prompt, model, randomness, openaiKey)

                maskList = re.findall(r"\[.+\]", response)

                if maskList:
                    maskValues = ast.literal_eval(maskList[0])

                # if there are too many values, reduce the list to 15 max
                if len(maskValues) > 15:
                    maskValues = maskValues[:15]

                # for each value found, make a mutated request with that value insted of the <op> token
                for value in maskValues:

                    # replace spaces with "+" characters for strings
                    if isinstance(value, str):
                        value = value.replace(" ", "+")

                    if mutationOperator not in ["addParameter", "modifyParameter", "resetParameters"] or re.fullmatch(r"(?P<parameter>\w+)=(?P<value>[^&]+)", value):

                        replaced = re.sub(r"(<op>=<op>|<op>)", str(value), maskedRequest)

                        # if there is an API key and it is not in the request, add it
                        if apiKey != "":
                            if f"appid={apiKey}" not in replaced:
                                replaced += f"&appid={apiKey}"

                        mutatedRequests.append(replaced)


            elif strategy == "singleMaskValue":

                requestText = f"Replace the <op> token mask in the following request: {maskedRequest}. Give me the complete new request which needs to be different from the following previous request: {request}. Only replace the <op> tokens in the request and nothing else. When the <op> token is a route or a parameter, try to find new valid routes and new parameters that have not been used yet. Do not invent route and parameter names, only answer with valid routes and parameters that exist in the API documentation."

                if apiKey != "":
                    requestText += f" Always include the following API key as parameter: {apiKey}"

                response = makeLLMRequest(requestText, model, randomness, openaiKey)

                mutatedRequest = re.findall(r"https?://[^\s]+", response)[0]

                mutatedRequests = [mutatedRequest]

        return {"strategy": strategy, "mutationOperator": mutationOperator, "initialRequest": request, "maskedRequest": maskedRequest, "maskValues": maskValues, "mutatedRequests": mutatedRequests}


    def findMutationOperator(self, request, nbBaseRoutes):

        # put all mutation operators in a list
        mutOpList = list(self.mutationOperators.keys())
        # initialize list of operators to remove
        removeList = []

        # analyze the seed to guide the mutation process
        requestDict = requestToDict(request)

        # if there is less than 1 parameter in the request, remove the removeParameter operator
        if len(requestDict["parameters"]["parsed"]) < 2:
            removeList.append("removeParameter")

            # if there are no parameters at all, remove other mutation operators related to parameters
            if len(requestDict["parameters"]["parsed"]) == 0:
                removeList.extend(["modifyParameter", "modifyParameterName", "modifyParameterValue"])

        # if there are less than the default number of API base routes, remove modifyRoute and removeRoute operators
        if len(requestDict["routes"]["parsed"]) <= nbBaseRoutes:
            removeList.extend(["removeRoute", "modifyRoute"])

        # remove all operators that are in the remove list from the mutation operator list
        for operator in removeList:
            if operator in mutOpList:
                mutOpList.remove(operator)

        # get a random mutation operator
        mutationOperator = random.choice(mutOpList)

        return mutationOperator


    def maskRequest(self, request, mutationOperator):

        # requestToDict will parse the request string into a dict
        requestDict = requestToDict(request)

        # if the request dict is empty, the request was not able to be parsed, so simply return the given request
        if requestDict == {}:
            return request

        # start with the base
        maskedRequest = requestDict["base"]

        # ROUTE MUTATION OPERATORS

        if mutationOperator == "addRoute":
            # add /<op> to the route dict list
            requestDict["routes"]["parsed"].append("/<op>")

        elif mutationOperator == "removeRoute":
            # if there is at least a route
            if len(requestDict["routes"]["parsed"]) > 0:
                # remove last route
                del requestDict["routes"]["parsed"][-1] # can change with random route and not last route for certain APIs, but generaly best this way

        elif mutationOperator == "modifyRoute":
            # replace last route with /<op>
            requestDict["routes"]["parsed"][-1] = "/<op>"

        # PARAMETER MUTATION OPERATORS

        elif mutationOperator == "addParameter":
            # add a new parameter name <op> with value <op>
            requestDict["parameters"]["parsed"].append({"name": "<op>", "value": "<op>"})

        elif mutationOperator == "removeParameter":
            # if there is at least one parameter
            if len(requestDict["parameters"]["parsed"]) > 0:
                # remove a random parameter
                randomIndex = random.randrange(len(requestDict["parameters"]["parsed"]))
                del requestDict["parameters"]["parsed"][randomIndex]

        elif mutationOperator == "modifyParameter":
            if len(requestDict["parameters"]["parsed"]) > 0:
                # change random existing parameter with <op>
                randomIndex = random.randrange(len(requestDict["parameters"]["parsed"]))
                requestDict["parameters"]["parsed"][randomIndex] = {"name": "<op>", "value": "<op>"}

        elif mutationOperator == "modifyParameterName":
            if len(requestDict["parameters"]["parsed"]) > 0:
                # change random existing parameter name with <op>
                randomIndex = random.randrange(len(requestDict["parameters"]["parsed"]))
                requestDict["parameters"]["parsed"][randomIndex] = {"name": "<op>", "value": requestDict["parameters"]["parsed"][randomIndex]["value"]}

        elif mutationOperator == "modifyParameterValue":
            if len(requestDict["parameters"]["parsed"]) > 0:
                # change random existing parameter value with <op>
                randomIndex = random.randrange(len(requestDict["parameters"]["parsed"]))
                requestDict["parameters"]["parsed"][randomIndex] = {"name": requestDict["parameters"]["parsed"][randomIndex]["name"], "value": "<op>"}

        elif mutationOperator == "resetParameters":
            # remove all but one parameter <op>
            requestDict["parameters"]["parsed"] = [{"name": "<op>", "value": "<op>"}]

        # reassemble the request from the mutated dict
        maskedRequest = dictToRequest(requestDict)

        return maskedRequest


    def generatePrompt(self, mutationOperator, maskedRequest, apiName):

        element1 = ""
        element2 = ""
        listElement = ""

        if mutationOperator in ["addRoute", "modifyRoute"]:
            element1 = "routes"
            element2 = "a route"
            listElement = "route"

        elif mutationOperator in ["addParameter", "modifyParameter", "resetParameters"]:
            element1 = "parameters"
            element2 = "a parameter"
            listElement = "parameter=value"

        elif mutationOperator == "modifyParameterName":
            element1 = "names"
            element2 = "a parameter name"
            listElement = "name"

        elif mutationOperator == "modifyParameterValue":
            element1 = "values"
            element2 = "a parameter value"
            listElement = "value"

        prompt = f'Give me a list containing all valid {element1} that can replace the <op> token in the following HTTP request: {maskedRequest}. Here is an explanation: The <op> token is hiding {element2} in a request to the {apiName}. The given results have to exist in the API and should be varied. The list needs to be of the structure ["{listElement} 1", "{listElement} 2", ...].'

        return prompt
