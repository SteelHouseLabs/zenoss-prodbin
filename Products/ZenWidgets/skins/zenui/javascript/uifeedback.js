(function() { // Let's use a private namespace, please

var Z = YAHOO.zenoss,            // Internal shorthand
    Y = YAHOO.util,              // Internal shorthand
    W = YAHOO.widget,            // Internal shorthand
    INFO     = 0,                // Same as in messaging.py
    WARNING  = 1,                // Same as in messaging.py
    CRITICAL = 2,                // Same as in messaging.py
    body = window.document.body, // Cache to save lookups
    Yowl = document.Yowl,        // Cache to save lookups
    pollInterval = 1000*30,      // 60 seconds
    priorities = ['low', 'high', 'emergency'],
    icons = ['/zport/dmd/img/agt_action_success-32.png',
             '/zport/dmd/img/messagebox_warning-32.png',
             '/zport/dmd/img/agt_stop-32.png'];

// Set up Yowl to be called by the Messenger
Yowl.register( 'zenoss', ['info'], ['info'],
    //Default image is a check mark
    '/zport/dmd/img/agt_action_success-32.png'
);

/**
 * Singleton object that accepts messages both directly and from periodic
 * polling of the server, and displays them in the browser.
**/
Z.Messenger = {

    // Start the polling off real good
    initialize: function() {
        this.startPolling(pollInterval); 
    },

    // Source of remote data
    datasource: new Y.XHRDataSource(
        // Pointer to live data
        "/zport/dmd/getUserMessages", 
        // Config object
        { 
            responseType: Y.XHRDataSource.TYPE_JSON, 
            responseSchema: {
                resultsList: "messages",
                fields:[
                    "sticky",
                    "title",
                    "image",
                    "body", 
                    {key: "priority", type: "number"}
                ],
                metaFields: {
                    totalRecords: 'totalRecords'
                }
            },
            maxCacheEntries: 0
        }
    ),

    // Callbacks for remote data; also handle connection errors
    callbacks: {
        success: function(r, o) {
            forEach(o.results, Z.Messenger.send);
        },

        failure: function() {
            Z.Messenger.connectionError();
        }
    },

    // Ask the server once for new messages
    checkMessages: function() {
        this.datasource.sendRequest(null, this.callbacks);
    },

    // Ask the server for messages once, then keep asking every interval ms
    startPolling: function(interval) {
        this.checkMessages();
        this.datasource.setInterval(interval, null, this.callbacks);
    },

    stopPolling: function() {
        this.datasource.clearAllIntervals();
    },

    // Shorthand to signify a connection error. Can be used by whatever.
    connectionError: function(msg) {
        var msg = msg || "Server connection error.";
        this.stopPolling();
        this.critical(msg);
    },

    // Put a message into the browser
    send: function(msgConfig) {
        var text     = msgConfig.body,
            title    = (msgConfig.title || "FYI"),
            priority = priorities[msgConfig.priority],
            image    = (msgConfig.image || icons[msgConfig.priority]),
            sticky   = (msgConfig.sticky || false);
        Yowl.notify('info', title, text, 'zenoss', image, sticky, priority);
    },

    // Shortcut to send severity INFO messages
    info: function(message) {
        this.send({
            title: "Information",
            body: message,
            priority: INFO
        })
    },

    // Shortcut to send severity WARNING messages
    warning: function(message) {
        this.send({
            title: "Warning",
            body: message,
            priority: WARNING
        })
    },

    // Shortcut to send severity CRITICAL messages
    critical: function(message) {
        this.send({
            title: "Red Alert",
            body: message,
            priority: CRITICAL,
            sticky: true
        })
    }


}; // end Z.Messenger


})(); // end private namespace

YAHOO.register("uifeedback", YAHOO.zenoss.Messenger, {});
