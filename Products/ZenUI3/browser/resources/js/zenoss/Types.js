(function(){

var _tm = {
    'DeviceLocation':   ["^/zport/dmd/Locations(/[A-Z][^/]*)*/?$"],
    'DeviceGroup':      ["^/zport/dmd/Groups(/[A-Z][^/]*)*/?$"],
    'DeviceClass':      ["^/zport/dmd/Devices(/[A-Z][^/]*)*/?$"],
    'Device':           ["^/zport/dmd/.*/devices/[^/]*/?$"]
}

Ext.ns('Zenoss.types');

var T = Zenoss.types;

Ext.apply(T, {

    TYPES: {},

    getAllTypes: function() {
        result = [];
        for (var k in T.TYPES) {
            result.push(k);
        }
        return result;
    }, // getAllTypes

    type: function(uid) {
        for (var type in T.TYPES) {
            if (T.TYPES[type]) {
                _f = true;
                Ext.each(T.TYPES[type], function(test) {
                    if (!_f) return;
                    _f = test.test(uid);
                });
                if (_f) return type;
            }
        }
    }, // getType

    register: function(config) {
        function addRegex(k, t) {
            var types = T.TYPES[k] = T.TYPES[k] || [];
            if (!(t instanceof RegExp)) {
                t = new RegExp(t);
            }
            if (!(t in types)) types.push(t);
        }
        for (var k in config) {
            var t = config[k];
            if (Ext.isString(t)) {
                addRegex(k, t);
            } else if (Ext.isArray(t)) {
                Ext.each(t, function(r) {
                    addRegex(k, r);
                });
            }

        }
    } // register

}); // Ext.apply

T.register(_tm);

})(); // End local scope
