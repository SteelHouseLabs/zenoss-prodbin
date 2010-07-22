(function(){ // Local scope

var ZI = Ext.namespace('Zenoss.inspector');

/**
 * Manages inspector windows to ensure that only one window matching `uid` is active at a time.
 */
ZI.SingleInstanceManager = Ext.extend(Object, {
    _instances: null,
    constructor: function() {
        this._instances = {};
    },
    register: function(uid, instance) {
        this.remove(uid);
        this._instances[uid] = instance;
        instance.on('destroy', function() { delete this._instances[uid]; }, this);
    },
    get: function(uid) {
        return this._instances[uid];
    },
    remove: function(uid) {
        Ext.destroyMembers(this._instances, uid);
    }
});

/**
 * Represents a single item in the inspector panel.
 *
 * config:
 *   - valueTpl An XTemplate that can be used to render the field. Will be passed the data that is passed to the
 *              inspector.
 */
ZI.InspectorProperty = Ext.extend(Ext.Container, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            cls: 'inspector-property',
            layout: 'form',
            items: [
                {
                    cls: 'inspector-property-label',
                    ref: 'labelItem',
                    xtype: 'label',
                    text: config.label ? config.label + ':' : ''
                },
                {
                    cls: 'inspector-property-value',
                    ref: 'valueItem',
                    text: config.value || '',
                    xtype: 'box',
                    tpl: config.valueTpl || '{.}'
                }
            ]
        });
        ZI.InspectorProperty.superclass.constructor.call(this, config);
    },
    setValue: function(t) {
        this.valueItem.update(t);
    },
    setLabel: function(t) {
        this.labelItem.setText(t + ':');
    }
});

Ext.reg('inspectorprop', ZI.InspectorProperty);


ZI.BaseInspector = Ext.extend(Ext.Panel, {
    _data: null,
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            defaultType: 'devdetailitem',
            layout: 'form',
            border: false,
            bodyBorder: false,
            items: [],
            titleTpl: '<div class="name">{name}</div>'
        });

        config.items = [
            {
                layout: 'hbox',
                cls: 'inspector-header',
                defaults: {border: false},
                ref: 'headerItem',
                items: [
                    {
                        cls: 'header-icon',
                        ref: 'iconItem',
                        xtype: 'box'
                    },
                    {
                        cls: 'header-title',
                        ref: 'titleItem',
                        xtype: 'label',
                        tpl: config.titleTpl
                    }
                ]
            },
            {
                xtype: 'container',
                cls: 'inspector-body',
                autoEl: 'div',
                layout: 'form',
                ref: 'bodyItem',
                defaultType: 'inspectorprop',
                items: config.items
            }
        ];

        ZI.BaseInspector.superclass.constructor.call(this, config);
    },
    setIcon: function(url) {
        this.headerItem.iconItem.getEl().setStyle({
            'background-image' : 'url(' + url + ')'
        });
    },
    onLayout: function(shallow, forceLayout) {
        ZI.BaseInspector.superclass.onLayout.call(this, shallow, forceLayout);

        if ( this._data ) {
            // Load any pending data
            var data = this._data;
            delete this._data;
            this.update(data);
        }
    },
    /**
     * Overwrite to add any properties dynamically from the data. Must return true if added any.
     */
    addNewDataItems: function(data) {
        return false;
    },
    update: function(data) {
        if ( this.rendered ) {
            if ( this.addNewDataItems(data) ) {
                this.doLayout();
            }

            // update all the children that have templates
            var self = this;
            this.cascade(function(item) {
                if ( item != self && item.tpl ) {
                    item.update(data);
                }

                return true;
            });

            if ( data.icon ) {
                this.setIcon(data.icon);
            }

            if ( this.ownerCt ) {
                this.ownerCt.doLayout(false, true);
            }
            else {
                this.doLayout(false, true);
            }
        }
        else {
            // Can't load the data yet, the components aren't ready
            // Set this up so we can set the data after layout
            this._data = data;
        }
    },
    /**
     * Add a property to the inspector panel for display.
     * @param label string
     * @param id string The key from the data to display
     */
    addProperty: function(label, id) {
        this.addPropertyTpl(label, '{[values.' + id + ' || \'\']}');
    },
    /**
     * Add a property to the inspector panel using a template to display.
     * @param label
     * @param tpl string A string in XTemplate format to display this property. Data values are in `values`.
     */
    addPropertyTpl: function(label, tpl) {
        this.bodyItem.add({
            xtype: 'inspectorprop',
            label: label,
            valueTpl: tpl
        });
    }
});

/**
 * An inspector that gets it's data via a directFn remote call.
 */
ZI.DirectInspector = Ext.extend(ZI.BaseInspector, {
    _contextUid: null,
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            directFn: Ext.emptyFn
        });

        ZI.DirectInspector.superclass.constructor.call(this, config);
    },
    initComponent: function() {
        ZI.DirectInspector.superclass.initComponent.call(this);
        this.addEvents('contextchange');
        this.on('contextchange', this._onContextChange, this);
    },
    refresh: function() {
        this.load();
    },
    load: function() {
        if ( this._contextUid ) {
            this.directFn(
                { uid: this._contextUid, keys: this.keys },
                function(result){
                    if ( result.success ) {
                        this.fireEvent('contextchange', result.data, this);
                    }
                },
                this
            );
        }
    },
    setContext: function(uid, load) {
        this._contextUid = uid;
        load = Ext.isDefined(load) ? load : true;

        if ( load ) {
            this.load();
        }
    },
    _onContextChange: function(data) {
        this.onData(data);
    },
    onData: function(data) {
        this.update(data);
    }
});

ZI.DeviceInspector = Ext.extend(ZI.DirectInspector, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            keys: ['ipAddress', 'device', 'deviceClass'],
            cls: 'inspector',
            titleTpl: '<div class="name"><a href="{uid}" target="_top">{name}</a></div><div class="info">{[Zenoss.render.DeviceClass(values.deviceClass.uid)]}</div><div class="info">{[Zenoss.render.ipAddress(values.ipAddress)]}</div>'
        });

        ZI.DeviceInspector.superclass.constructor.call(this, config);

        this.addPropertyTpl(_t('Events'), '{[Zenoss.render.events(values.events, 4)]}');
        this.addPropertyTpl(_t('Device Status'), '{[Zenoss.render.pingStatus(values.status)]}');
        this.addProperty(_t('Production State'), 'productionState');
        this.addPropertyTpl(_t('Location'), '{[(values.location && values.location.name) || ""]}');
    }
});

Ext.reg('deviceinspector', ZI.DeviceInspector);

ZI.ComponentInspector = Ext.extend(ZI.DirectInspector, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            keys: ['ipAddress', 'device'],
            cls: 'inspector',
            titleTpl: '<div class="name">{name}</div><div class="info"><a href="{[values.device.uid]}" target="_top">{[values.device.device]}</a></div><div class="info">{[Zenoss.render.ipAddress(values.ipAddress)]}</div>'
        });

        config.items = [
            {
                label: _t('Events'),
                valueTpl: '{[Zenoss.render.events(values.events, 4)]}'
            }
        ];

        ZI.ComponentInspector.superclass.constructor.call(this, config);
    }
});

Ext.reg('componentinspector', ZI.ComponentInspector);

var windowManager = new ZI.SingleInstanceManager();
ZI.createWindow = function(uid, xtype, x, y) {
    var win = new Ext.Window({
        x: (x || 0),
        y: (y || 0),
        cls: 'inspector-window',
        frame: true,
        constrain: true,
        resizable: false,
        layout: 'form',
        width: 300,
        plain: true,
        border: false,
        items: [{
            xtype: xtype,
            ref: 'panelItem'
        }]
    });

    windowManager.register(uid, win);
    return win;
}

ZI.registeredInspectors = {
    device : 'deviceinspector'
};

ZI.registerInspector = function(inspector_type, inspector_xtype) {
    ZI.registeredInspectors[inspector_type.toLowerCase()] = inspector_xtype
}

ZI.show = function(uid, x, y) {
    Zenoss.remote.DeviceRouter.getInfo({ uid: uid }, function(result) {
        if ( result.success ) {
            // Grasping at straws but assume it's a component unless otherwise stated
            var xtype = 'componentinspector';

            var itype = result.data.inspector_type || result.data.meta_type;
            if ( itype ) {
                itype = itype.toLowerCase();
                if ( ZI.registeredInspectors[itype] ) {
                    xtype = ZI.registeredInspectors[itype];
                }
            }

            var win = ZI.createWindow(uid, xtype, x, y);
            win.panelItem.setContext(uid, false);
            win.panelItem.update(result.data);
            win.show();
        }
    });
};

})();
