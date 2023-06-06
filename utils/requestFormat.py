import re


def requestToDict(request):

    requestExp = r"(?P<base>https?://[^/]+)(?P<routes>[^?]+)(?P<parameters>\?.+)?"
    routeExp = r"(?P<route>/[^/]+)"
    parameterExp = r"(?P<parameter>\w+)=(?P<value>[^&]+)"
    requestDict = {}

    # remove all whitespaces
    request = request.replace(" ", "")

    parsedRequest = re.search(requestExp, request)

    # if the request has at least a base and a route expression (parameter group is optional), analyze it
    if parsedRequest:
        requestDict = {"base": parsedRequest.group("base"), "routes": {"unparsed": parsedRequest.group("routes"), "parsed": []}, "parameters": {"unparsed": parsedRequest.group("parameters"), "parsed": []}}

        # if routes do not end with a '/', add it
        if requestDict["routes"]["unparsed"][-1] != "/":
            requestDict["routes"]["unparsed"] += "/"

        routeList = re.findall(routeExp, requestDict["routes"]["unparsed"])

        if routeList:
            requestDict["routes"]["parsed"] = routeList

        # if the parameter group is not None
        if requestDict["parameters"]["unparsed"]:
            parameterList = re.findall(parameterExp, requestDict["parameters"]["unparsed"])

            if parameterList:
                for parameter in parameterList:
                    requestDict["parameters"]["parsed"].append({"name": parameter[0], "value": parameter[1]})
        else:
            requestDict["parameters"]["unparsed"] = ""

    return requestDict


def dictToRequest(dict):

    # start with the base
    request = dict["base"]

    # routes
    for route in dict["routes"]["parsed"]:
        request += route

    # add '/' after last route
    request += "/"

    # parameters
    if len(dict["parameters"]["parsed"]) > 0:
        request += "?" # '?' to indicate start of parameters

        for index in range(len(dict["parameters"]["parsed"])):
            parameter = dict["parameters"]["parsed"][index]
            request += parameter["name"] + "=" + parameter["value"]

            # if there are still parameters next in the list, add a '&' separator
            if index < len(dict["parameters"]["parsed"]) - 1:
                request += "&"

    return request
