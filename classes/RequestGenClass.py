import os, json, re, random, ast, time
from utils.makeRequest import makeHTTPRequest, makeLLMRequest
from utils.requestFormat import requestToDict, dictToRequest
from utils.requestValidity import getRequestValidity


class RequestGen:


    def __init__(self, name, apiKey, openaiKey, base, seed, model, mutation, logger):

        self.name = name
        self.apiKey = apiKey
        self.openaiKey = openaiKey
        self.model = model
        self.mutation = mutation
        self.logger = logger

        # initialize other variables
        self.grammarDict = {}
        self.specs = {"routes": [], "parameters": {}} ##################
        self.seedList = []
        self.docUrl = ""
        self.apiUrl = ""
        self.nbBaseRoutes = 0
        self.fileName = name.replace(" ", "_") # replace spaces with underscores for file names
        # define the grammar and seed path location for easy access
        self.grammarPath = f"./outputs/grammars/{self.fileName}_grammar.txt"
        self.seedPath = f"./outputs/seeds/{self.fileName}_seeds.txt"
        self.basePath = f"./outputs/bases/{self.fileName}_base.txt"

        # check if request grammar already exists in /outputs/grammars
        if os.path.exists(self.grammarPath):
            # load it
            with open(self.grammarPath, "r") as openfile:
                self.grammarDict = json.load(openfile)

        # check if request seed list already exists in /outputs/seeds
        if os.path.exists(self.seedPath):
            # load it
            with open(self.seedPath, "r") as openfile:
                self.seedList = openfile.read().splitlines()

        # check if API base and doc already exist in /outputs/bases
        if os.path.exists(self.basePath):
            # load it
            with open(self.basePath, "r") as openfile:
                bases = json.load(openfile)
                self.docUrl = bases["doc"]
                self.apiUrl = bases["base"]
                self.nbBaseRoutes = bases["nbBaseRoutes"]
        else:
            self.findApiUrls(base, seed)

        # log api setup info
        self.logger.logMessage("API SETUP INFORMATION", "title", "blue", True)
        self.logger.logMessage("API Name", "bullet", "purple", True, self.name)
        if self.apiKey != "":
            self.logger.logMessage("API Key", "bullet", "purple", False, self.apiKey)
        self.logger.logMessage("OpenAI API Key", "bullet", "purple", False, self.openaiKey)
        self.logger.logMessage("LLM Model", "bullet", "purple", False, self.model)
        self.logger.logMessage("API Documentation URL", "bullet", "purple", False, self.docUrl)
        self.logger.logMessage("API Base URL", "bullet", "purple", False, self.apiUrl)
        self.logger.logMessage("API Seed Example", "bullet", "purple", False, self.seedList[0])


    def findApiUrls(self, base, seed):

        self.logger.logMessage("FINDING API URLs", "title", "blue", True)

        # api documentation url
        response = makeLLMRequest(f"Give me the URL of the documentation for API requests to the {self.name}.", self.model, 0, self.openaiKey)
        self.docUrl = re.findall(r"https?://[^\s]+", response)[0]

        # api base url
        if base == "":
            response = makeLLMRequest(f"Give me the base URL for requests to the {self.name}. Do not forget to include the version of the API in the URL if it exists.", self.model, 0, self.openaiKey)
            self.apiUrl = re.findall(r"https?://[^\s]+", response)[0]
        else:
            self.apiUrl = base

        # example api seed
        if seed == "":
            text = f"Give me an example of a valid GET HTTP request containing various parameters that can be made to the {self.name}."
            if self.apiKey != "":
                text += f" Always include the following API key as parameter: {self.apiKey}"

            response = makeLLMRequest(text, self.model, 0, self.openaiKey)
            seed = re.findall(r"https?://[^\s]+", response)[0]

        # check if the given seed is valid
        validity = getRequestValidity(seed, "get")

        if validity["validity"] == "validRequest":
            # if valid request, update the grammar
            self.updateSeedList(seed)
            self.updateGrammar(seed)
            self.logger.logMessage("Added a valid API request as default seed", "arrow", "yellow", True)

        # if no valid seed was found, add the base api url as seed
        else:
            self.updateSeedList(self.apiUrl)
            self.updateGrammar(self.apiUrl)
            self.logger.logMessage("Added the base API URL as default seed", "arrow", "yellow", True)

        # find the number of base routes
        baseDict = requestToDict(self.apiUrl)
        self.nbBaseRoutes = len(baseDict["routes"]["parsed"])

        # add base url info to file
        bases = {"doc": self.docUrl, "base": self.apiUrl, "nbBaseRoutes": self.nbBaseRoutes}
        with open(self.basePath, "w") as outfile:
            json.dump(bases, outfile, indent=4)


    def findRequests(self, iterations, seedLimiting, seed=""):

        self.logger.logMessage("STARTING REQUEST MUTATION", "title", "blue", True)

        statusDict = {} # list to keep track of status codes obtained

        # if there are no seeds, initialize URLs
        if len(self.seedList) == 0:
            self.findApiUrls()

        # if there is a given seed, add it the the seed list
        if seed != "":
            self.seedList.append(seed)

        for i in range(iterations):

            self.logger.logMessage("MUTATION", "title", "blue", True)

            # get a random seed from the seed list
            requestSeed = self.seedList[random.randrange(len(self.seedList))]

            # let the mutation class handle the mutation process, and then capture all info
            mutationDict = self.mutation.applyMutationStrategy("allMaskValues", requestSeed, self.nbBaseRoutes, self.name, self.model, 0.7, self.openaiKey, self.apiKey)

            # log mutation parameters
            self.logger.logMessage("Strategy", "bullet", "purple", True, mutationDict["strategy"])
            self.logger.logMessage("Mutation Operator", "bullet", "purple", False, mutationDict["mutationOperator"])
            self.logger.logMessage("Initial Request", "bullet", "purple", False, mutationDict["initialRequest"])
            self.logger.logMessage("Masked Request", "bullet", "purple", False, mutationDict["maskedRequest"])
            self.logger.logMessage("Possible Values", "bullet", "purple", False, mutationDict["maskValues"])

            # if all values are of type int, it is probably random int values so only keep one
            if len(mutationDict["maskValues"]) > 0 and all(isinstance(value, int) for value in mutationDict["maskValues"]):
                mutationDict["mutatedRequests"] = [mutationDict["mutatedRequests"][0]]
                self.logger.logMessage("Reduced generated requests due to same numeric type", "arrow", "yellow")

            # keep track of the number of added requests
            addedParameterSeed = False

            # check if the mutated requests are valid
            for mutatedRequest in mutationDict["mutatedRequests"]:

                self.logger.logMessage(f"Verifying request validity", "arrow", "blue", True, mutatedRequest)

                # check the validity of the mutated request
                validity = getRequestValidity(mutatedRequest, "get")
                self.logger.logMessage("Validity", "bullet", "purple", False, validity)

                # add the status code to the status dictionary
                if validity["status"] not in statusDict:
                    statusDict[validity["status"]] = 0
                statusDict[validity["status"]] += 1

                # add the mutated request to the seed list if valid and not already in list
                if validity["validity"] == "validRequest":

                    # check for potential in-page error
                    title = validity["title"].lower()

                    if "error" in title:
                        self.logger.logMessage("Detected a potential in-page error", "arrow", "yellow")

                    if mutatedRequest not in self.seedList:

                        # if limiting the seeds, only add a single seed resulting from a parameter mutation operator; Still add all seeds from route mutation operators
                        if seedLimiting:
                            # update the grammar
                            self.updateGrammar(mutatedRequest)

                            # if valid request, update the seed list and the grammar
                            # if the mutated requests modify parameters, only add one to avoid getting too many similar seeds
                            if mutationDict["mutationOperator"] in ["addRoute", "removeRoute", "modifyRoute", "removeParameter"]:
                                self.updateSeedList(mutatedRequest)
                                self.logger.logMessage("Added in seeds", "arrow", "green")

                            elif not addedParameterSeed:
                                self.updateSeedList(mutatedRequest)
                                self.logger.logMessage("Only added a single seed to avoid similar request overflow", "arrow", "yellow")
                                addedParameterSeed = True

                            else:
                                self.logger.logMessage("Rejected in seeds to avoid similar request overflow", "arrow", "red")

                        # if not limiting seeds, automatically add valid requests to the seed list
                        else:
                            self.updateSeedList(mutatedRequest)
                            self.updateGrammar(mutatedRequest)
                            self.logger.logMessage("Added in seeds", "arrow", "green")

                    else:
                        self.logger.logMessage("Already in seeds", "arrow", "yellow")

                else:
                    self.logger.logMessage("Rejected in seeds", "arrow", "red")

            # print iteration nb
            self.logger.logMessage("Progress", "arrow", "yellow", True, f"{i+1}/{iterations}")

        # print obtained request validity results
        self.logger.logMessage("Status Code Results", "bullet", "purple", True, statusDict)

        # print found elements
        self.logger.logMessage("Found Elements", "bullet", "purple", True, self.specs)


    def updateGrammar(self, request):

        # Update the grammar dict and file
        requestDict = requestToDict(request)

        if requestDict != {}:
            base = requestDict["base"]
            route = requestDict["routes"]["unparsed"]
            parameters = requestDict["parameters"]["parsed"]

            if base not in self.grammarDict:
                self.grammarDict[base] = {}

                self.specs["routes"].append(base) #########################

            if route not in self.grammarDict[base]:
                self.grammarDict[base][route] = {}
                self.logger.logMessage(f"New route found", "arrow", "green", False, route)

                self.specs["routes"].append(route) #######################

            for parameter in parameters:
                if parameter["name"] not in self.grammarDict[base][route]:
                    self.grammarDict[base][route][parameter["name"]] = []
                    self.logger.logMessage(f"New parameter found", "arrow", "green", False, parameter["name"])

                if parameter["value"] not in self.grammarDict[base][route][parameter["name"]]:
                    self.grammarDict[base][route][parameter["name"]].append(parameter["value"])
                    self.logger.logMessage(f"New value found for parameter '{parameter['name']}'", "arrow", "green", False, parameter["value"])

                ###########################
                if parameter["name"] not in self.specs["parameters"]:
                    self.specs["parameters"][parameter["name"]] = []

                ############################
                if parameter["value"] not in self.specs["parameters"][parameter["name"]]:
                    self.specs["parameters"][parameter["name"]].append(parameter["value"])

        # dump grammar in file
        with open(self.grammarPath, "w") as outfile:
            json.dump(self.grammarDict, outfile, indent=4)


    def updateSeedList(self, request):

        # Update the seed list and file
        if request not in self.seedList:
            self.seedList.append(request)
            # add to seed file
            with open(self.seedPath, "a") as outfile:
                outfile.write(f"{request}\n")


    def askRequests(self):

        prompt = "Generate 20 examples of complex GET HTTP requests that can be made to the MusicBrainz API web service. The example requests need to be in a Python list of the following structure: [request 1, request 2, ...]. The requests should all be valid, have various routes and different parameters. The requests cannot be too similar. Do not forget to include the base route of the API in each request."

        """
        if self.apiKey != "":
            prompt += f" The API key is {self.apiKey}."
        """

        print(prompt)

        start = time.time()
        response = makeLLMRequest(prompt, "text-davinci-003", 0.7, self.openaiKey)
        print(response)
        end = time.time()

        print(f"- COMPLETION TIME: {end - start}")

        requestList = re.findall(r"https?://[^\s']+", response)

        print(len(requestList))

        nbValid = 0

        for request in requestList:

            print(f"- REQUEST: {request}")
            validity = getRequestValidity(request, "get")
            print(f"- VALIDITY: {validity['validity']}")
            if validity["validity"] == "validRequest":
                nbValid += 1
                self.updateSeedList(request)
                self.updateGrammar(request)

        print(f" - TOTAL VALID: {nbValid}/{len(requestList)}")
