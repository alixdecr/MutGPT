import re
from utils.makeRequest import makeHTTPRequest


def getRequestValidity(request, method):

    try:
        response = makeHTTPRequest(request, method)
        statusCode = response.status_code

        # find validity
        if statusCode in range(500, 600):
            validity = "validRequestServerError"

        elif statusCode in range(400, 500):
            validity = "invalidRequest"

        else:
            validity = "validRequest"

        # find page title
        titles = re.findall(r"<title>(.+)</title>", response.text)

        if titles:
            title = titles[0]
            if len(title) > 30:
                title = title[:30] + "..."
        else:
            title = "No Title Found"

        # find page return content
        contents = re.findall(r"({.+})", response.text)

        # if there is content, display its first 30 characters
        if contents:
            content = contents[0]
            if len(content) > 30:
                content = content[:30] + "..."
        else:
            content = "No Content Found"

    # if error, too long to load content
    except:
        statusCode = "408"
        validity = "invalidRequest"
        title = "Request Timeout"
        content = "Request Timeout"

    return {"status": statusCode, "validity": validity, "title": title, "content": content}
