src = """
window.pywebview = {
    token: '%(token)s',
    platform: '%(platform)s',
    api: {},

    _createApi: function(funcList) {
        for (var i = 0; i < funcList.length; i++) {
            var funcName = funcList[i].func;
            var params = funcList[i].params;

            var funcBody =
                "var __id = (Math.random() + '').substring(2); " +
                "var promise = new Promise(function(resolve, reject) { " +
                    "window.pywebview._checkValue('" + funcName + "', resolve, reject, __id); " +
                "}); " +
                "window.pywebview._bridge.call('" + funcName + "', arguments, __id); " +
                "return promise;"

            window.pywebview.api[funcName] = new Function(params, funcBody)
            window.pywebview._returnValues[funcName] = {}
        }
    },

    _bridge: {
        call: function (funcName, params, id) {
            switch(window.pywebview.platform) {
                case 'mshtml':
                case 'cef':
                case 'qtwebkit':
                    return window.external.call(funcName, pywebview._stringify(params), id);
                case 'chromium':
                    return window.chrome.webview.postMessage([funcName, params, id]);
                case 'cocoa':
                case 'gtk':
                    return window.webkit.messageHandlers.jsBridge.postMessage(pywebview._stringify({funcName, params, id}));
                case 'qtwebengine':
                    if (!window.pywebview._QWebChannel) {
                        setTimeout(function() {
                            window.pywebview._QWebChannel.objects.external.call(funcName, pywebview._stringify(params), id);
                        }, 100)
                    } else {
                        window.pywebview._QWebChannel.objects.external.call(funcName, pywebview._stringify(params), id);
                    }
                    break;
            }
        }
    },

    _checkValue: function(funcName, resolve, reject, id) {
         var check = setInterval(function () {
            var returnObj = window.pywebview._returnValues[funcName][id];
            if (returnObj) {
                var value = returnObj.value;
                var isError = returnObj.isError;

                delete window.pywebview._returnValues[funcName][id];
                clearInterval(check);

                if (isError) {
                    var pyError = JSON.parse(value);
                    var error = new Error(pyError.message);
                    error.name = pyError.name;
                    error.stack = pyError.stack;

                    reject(error);
                } else {
                    resolve(JSON.parse(value));
                }
            }
         }, 1)
    },

    _returnValues: {},
    _asyncCallback: function(result, id) {
        window.pywebview._bridge.call('asyncCallback', result, id)
    },
    _isPromise: function (obj) {
        return !!obj && (typeof obj === 'object' || typeof obj === 'function') && typeof obj.then === 'function';
    },

    _stringify: function(obj, depth=0, visited=new WeakSet()) {
        try {
            if (obj instanceof Node) return pywebview.domJSON.toJSON(obj, { metadata: false });
            if (obj instanceof Window) return 'Window';
            if (typeof obj === 'function') return 'function';
            if (typeof obj === 'boolean' || typeof obj === 'number' || typeof obj === 'string') return obj;

            if (visited.has(obj)) {
                return '[Circular Reference]';
            }

            if (typeof obj === 'object' && obj !== null) {
                visited.add(obj);

                if (Array.isArray(obj)) {
                    const arr = obj.map(value => pywebview._stringify(value, depth + 1, visited));
                    visited.delete(obj);
                    return depth ? arr : JSON.stringify(arr);
                }

                const newObj = {};
                for (const key in obj) {
                    newObj[key] = pywebview._stringify(obj[key], depth + 1, visited);
                }
                visited.delete(obj);
                return depth ? newObj : JSON.stringify(newObj);
            }

            return JSON.stringify(obj);
        } catch (e) {
            console.error(e)
            return e.toString();
        }
    }
}
window.pywebview._createApi(%(func_list)s);

if (window.pywebview.platform == 'qtwebengine') {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        window.pywebview._QWebChannel = channel;
        window.dispatchEvent(new CustomEvent('pywebviewready'));
    });
} else {
    window.dispatchEvent(new CustomEvent('pywebviewready'));
}
"""
