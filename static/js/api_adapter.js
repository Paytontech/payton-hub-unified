/**
 * Payton Hub API Adapter
 * Mimics Google Apps Script's google.script.run for Flask Backend
 */
window.google = window.google || {};
window.google.script = window.google.script || {};

class ScriptRunProxy {
    constructor() {
        this._onSuccess = null;
        this._onFailure = null;
    }

    withSuccessHandler(fn) {
        this._onSuccess = fn;
        return this;
    }

    withFailureHandler(fn) {
        this._onFailure = fn;
        return this;
    }

    // This will be called for any function name
    async _callApi(functionName, args) {
        try {
            const response = await fetch('/api/gas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    function: functionName,
                    args: args
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (this._onSuccess) {
                this._onSuccess(result);
            }
        } catch (error) {
            console.error(`Error calling ${functionName}:`, error);
            if (this._onFailure) {
                this._onFailure(error);
            }
        }
    }
}

// Create the proxy handler
const proxyHandler = {
    get: function(target, prop) {
        if (prop === 'withSuccessHandler' || prop === 'withFailureHandler') {
            return target[prop].bind(target);
        }
        
        // Return a function that calls _callApi
        return function(...args) {
            target._callApi(prop, args);
        };
    }
};

window.google.script.run = new Proxy(new ScriptRunProxy(), proxyHandler);

console.log("Payton API Adapter Initialized");
