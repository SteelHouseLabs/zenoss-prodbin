(function(){

Ext.ns('Zenoss.render');

// templates for the events renderer
var iconTemplate = new Ext.Template(
    '<td class="severity-icon-small {severity}">{count}</td>');
iconTemplate.compile();

var rainbowTemplate = new Ext.Template(
    '<table class="eventrainbow"><tr>{cells}</tr></table>');
rainbowTemplate.compile();
                     
Ext.apply(Zenoss.render, {

    pingStatus: function(bool) {
        return bool ? 'Up' : 'Down';
    },

    ipAddress: function(ip) {
        return (ip instanceof String) ? ip : Zenoss.util.num2dot(ip);
    },

    severity: function(sev) {
        return '<div class="severity-icon-small '+
            Zenoss.util.convertSeverity(sev) +
            '"'+'><'+'/div>';
    },

    // renders availability as a percentage with 3 digits after decimal point
    availability: function(value) {
        return Ext.util.Format.number(value*100, '0.000%');
    },

    evstatus: function(evstatus) {
        return '<div class="status-icon-small '+evstatus.toLowerCase()+'"><'+'/div>';
    },

    events: function(value) {
        var result = '';
        Ext.each(['critical', 'error', 'warning'], function(severity) {
            result += iconTemplate.apply({severity: severity,
                                          count:value[severity]});
        });
        return rainbowTemplate.apply({cells: result});
    },

    /* 
     * Given a uid, determines the type of the object and passes rendering
     * off to the appropriate rendering function.
     * e.g. Zenoss.render.link('/zport/dmd/Devices/Server') =>
     * <a href="/zport/dmd/itinfrastructure#devices:/Devices/Server/Linux">...
     *
     * Can also just accept a url and name for wrapping in an anchor tag, by
     * passing in null for the first argument.
     */
    link: function(uid, url, name) {
        if (!url) {
            var type = Zenoss.types.type(uid),
                renderer = Zenoss.render[type];
            if (renderer) {
                return renderer(uid, name);
            }
        }
        return '<a href="'+url+'">'+name+'</a>';
    },

    linkFromGrid: function(name, col, record) {
        var item;
        if (typeof(record.data[col.id]) == 'object') {
            item = record.data[col.id];
            
            if (item.uid) {
                return Zenoss.render.link(item.uid, null, item.text);
            }
            return item.text;
        }
        
        return name;
    },
        
    Device: function(uid, name) {
        // For now, link to the old device page
        return Zenoss.render.link(null, uid+'/devicedetail', name);
    },

    DeviceClass: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Devices/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#devices:.zport.dmd.Devices' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    },

    DeviceLocation: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Locations/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#locs:.zport.dmd.Locations' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    },

    DeviceGroup: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Groups/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#groups:.zport.dmd.Groups' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    },

    DeviceComponent: function(url, name) {
        // TODO once these pages are built fix the link
        return Zenoss.render.link(null, url, name);
    },
        
    EventClass: function(uid, name) {
        // TODO make this point to the correct place once we have the event
        // class pages
        var value = uid.replace(/^\/zport\/dmd\/Events/, '');
        var url = '/zport/dmd/Events/evconsole#eventClass:.zport.dmd.Events' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    }

}); // Ext.apply

})(); // End local namespace
