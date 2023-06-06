from classes.LoggerClass import Logger
from classes.RequestGenClass import RequestGen
from classes.RequestMutationClass import RequestMutation


def main():

    # STEP 0: INSTANTIATE THE LOGGER, PRINT MUTGPT TOOL
    logger = Logger()
    logger.logMessage("MutGPT - The Automatic API Request Mutation and Specification Inferring Tool", "title", "blue", True)
    print("")

    # STEP 1: ASK FOR WEB SERVICE DETAILS
    name = "GBIF Species API"
    apiKey = "" # leave empty if the API does not require a key
    openaiKey = "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"
    model = "text-davinci-003"
    base = "" # leave empty for attempt to find a valid API base
    seed = "" # leave empty for attempt to find a valid seed
    nbMutations = 20
    seedLimiting = False

    # STEP 2: INSTANTIATE THE MUTATION AND REQUEST GENERATOR CLASS
    mutation = RequestMutation()
    webServiceReq = RequestGen(name, apiKey, openaiKey, base, seed, model, mutation, logger)

    # STEP 3: START REQUEST FINDING PROCESS
    webServiceReq.findRequests(nbMutations, seedLimiting)


if __name__ == "__main__":

    main()
