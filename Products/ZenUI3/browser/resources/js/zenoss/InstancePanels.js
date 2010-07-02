/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

(function(){

Ext.ns('Zenoss');

var InstanceColumnModel = Ext.extend(Ext.grid.ColumnModel, {

    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            defaults: {
                menuDisabled: true
            },
            columns: [{
                    id: 'device',
                    dataIndex: 'device',
                    header: _t('Device'),
                    width: 200,
                    renderer: function(device, row, record){
                        return Zenoss.render.link(device.uid, undefined,
                                                  device.name);
                   }
                }, {
                    id: 'name',
                    dataIndex: config.nameDataIndex || 'name',
                    header: _t('Name'),
                    width: 400
                }, {
                    id: 'monitored',
                    dataIndex: 'monitored',
                    header: _t('Monitored'),
                    width: 70,
                    sortable: true
                }, {
                    id: 'status',
                    dataIndex: 'status',
                    header: _t('Status'),
                    renderer: Zenoss.render.pingStatus,
                    width: 60
                }
            ]
        });
        InstanceColumnModel.superclass.constructor.call(this, config);
    }

});

/**
 * Device data store definition
 * @constructor
 */
Zenoss.InstanceStore = Ext.extend(Ext.ux.grid.livegrid.Store, {

    constructor: function(config) {
        Ext.applyIf(config, {
            bufferSize: 50,
            proxy: new Ext.data.DirectProxy({
                directFn: config.directFn
            }),
            reader: new Ext.ux.grid.livegrid.JsonReader({
                root: 'data',
                idProperty: 'uid',
                fields: [
                    {name: 'device'},
                    {name: config.nameDataIndex || 'name'},
                    {name: 'monitored'},
                    {name: 'status'}
                ]
            })
        });
        Zenoss.InstanceStore.superclass.constructor.call(this, config);
    }

});

Ext.reg('InstanceStore', Zenoss.InstanceStore);

Zenoss.SimpleInstanceGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            autoExpandColumn: 'name',
            stripeRows: true,
            cm: new InstanceColumnModel({
                nameDataIndex: config.nameDataIndex
            }),
            store: {
                xtype:'InstanceStore',
                directFn: config.directFn,
                nameDataIndex: config.nameDataIndex
            }
        });
        Zenoss.SimpleInstanceGridPanel.superclass.constructor.call(this, config);
    },

    setContext: function(uid) {
        this.getStore().load({params:{uid:uid}});
    }

});

Ext.reg('SimpleInstanceGridPanel', Zenoss.SimpleInstanceGridPanel);


// supply the instances implementation in the config
Zenoss.SimpleCardPanel = Ext.extend(Ext.Panel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'card',
            activeItem: 0,
            height: Math.min(((Ext.getCmp('viewport').getHeight() - 75)/5)+30, 200),
            tbar: {
                xtype: 'consolebar',
                title: 'Display: ',
                leftItems: [{
                    xtype: 'select',
                    ref: '../displaySelect',
                    mode: 'local',
                    value: config.instancesTitle,
                    store: [config.instancesTitle, 'Configuration Properties'],
                    listeners: {
                        select: function(displaySelect, record, index) {
                            displaySelect.refOwner.getLayout().setActiveItem(index);
                        }
                    }
                }]
            },
            items: [
                config.instances,
            {
                xtype: 'backcompat',
                ref: 'zPropertyEdit',
                viewName: 'zPropertyEdit',
                refreshOnContextChange: true,
                listeners: config.zPropertyEditListeners
            }]
        });
        Zenoss.SimpleCardPanel.superclass.constructor.call(this, config);
    },

    setContext: function(uid) {
        this.items.each(function(item) {
            item.setContext(uid);
        });
    }

});

Ext.reg('simplecardpanel', Zenoss.SimpleCardPanel);

// has the instances used by the Processes page and the two Services pages
Zenoss.InstanceCardPanel = Ext.extend(Zenoss.SimpleCardPanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            instances: [{
                xtype: 'SimpleInstanceGridPanel',
                ref: 'instancesGrid',
                directFn: config.router.getInstances,
                nameDataIndex: config.nameDataIndex || "name"
            }]
        });
        Zenoss.InstanceCardPanel.superclass.constructor.call(this, config);
    }

});

Ext.reg('instancecardpanel', Zenoss.InstanceCardPanel);


})();
