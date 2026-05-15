/**
 * Payton Hub API Adapter
 * Mimics Google Apps Script's google.script.run for Flask Backend
 * Fixed chaining by returning the proxy instance
 */
window.google = window.google || {};
window.google.script = window.google.script || {};

class ScriptRunProxy {
    constructor() {
        this._onSuccess = null;
        this._onFailure = null;
        this._proxy = null; // Reference to the proxy for chaining
    }

    withSuccessHandler(fn) {
        this._onSuccess = fn;
        return this._proxy || this;
    }

    withFailureHandler(fn) {
        this._onFailure = fn;
        return this._proxy || this;
    }

    async _callApi(functionName, args) {
        try {
            console.log(`Adapting GAS Call: ${functionName}`, args);
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
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log(`GAS Call ${functionName} Success:`, result);
            
            if (this._onSuccess) {
                this._onSuccess(result);
            }
        } catch (error) {
            console.error(`GAS Call ${functionName} Error:`, error);
            if (this._onFailure) {
                this._onFailure(error);
            }
        }
    }
}

// Create the core instance
const scriptRunInstance = new ScriptRunProxy();

// Create the proxy handler
const proxyHandler = {
    get: function(target, prop) {
        // Special case for handlers
        if (prop === 'withSuccessHandler' || prop === 'withFailureHandler') {
            return target[prop].bind(target);
        }
        
        // If it's anything else, treat it as a GAS function call
        return function(...args) {
            target._callApi(prop, args);
        };
    }
};

// Initialize the proxy
const runProxy = new Proxy(scriptRunInstance, proxyHandler);
scriptRunInstance._proxy = runProxy; // Store proxy reference for chaining

// Set global
window.google.script.run = runProxy;

console.log("Payton API Adapter Initialized - Proxy Chaining Active");
