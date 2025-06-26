class MainHttpClient {

    constructor(host) {
        this.host = host;
        this.version = chrome.runtime.getManifest().version;
    }

    getUrl(path) {
        return this.host + path;
    }

    makeRequestBody(params) {
        return {
            tab_id: Globals.tab_id,
            user_id: Globals.user_id,
            url: document.URL,
            extension_version: this.version,
            data: JSON.stringify(params)
        };
    }

    postRequest(path, params,
        callback = function (d) { },
        callback_err = function (s) { }) {
        let body = this.makeRequestBody(params);

        // Debug logging
        console.log("Sending request to:", this.getUrl(path));
        console.log("Request params:", params);
        console.log("Formatted body:", body);

        fetch(this.getUrl(path), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        })
            .then(response => {
                // Debug logging
                console.log("Response status:", response.status);
                // console.log("Response headers:", response.headers);

                if (response.ok) {
                    return response.json();
                } else {
                    throw new Error('Network response was not ok: ' + response.statusText);
                }
            })
            .then(data => {
                // console.log("Response data:", data);
                callback(data);
            })
            .catch(error => {
                console.log(path, " failed with error:", error.message, "Calling error callback");
                callback_err(error.message);
            });
    }
    
    logEvent(eventType, params = {}) {
        params['event_type'] = eventType;
        //console.log("Logging:", params)
        //this.postRequest("/event", params);
    }


}

let client = new MainHttpClient(Globals["server_url"])