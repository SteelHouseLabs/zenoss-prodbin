/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

Ext.onReady(function(){

var REMOTE = Zenoss.remote.DeviceRouter,
    UID = Zenoss.env.device_uid;

REMOTE.getProductionStates({}, function(d){
    Zenoss.env.PRODUCTION_STATES = d;
});

REMOTE.getPriorities({}, function(d){
    Zenoss.env.PRIORITIES = d;
});

function selectOnRender(n, sm) {
    sm.selectRow(n);
}

function deviceColumnDefinitions() {
    var defs = Zenoss.env.COLUMN_DEFINITIONS;
    return Zenoss.util.filter(defs, function(d){
        return d.id != "device";
    });
}

function refreshComponentTreeAndGrid(compType) {
    var tree = Ext.getCmp('deviceDetailNav').treepanel,
        sm = tree.getSelectionModel(),
        detailnav = Ext.getCmp('deviceDetailNav'),
        sel = sm.getSelectedNode(),
        compsNode = tree.getRootNode().findChildBy(function(n){
            return n.get("text")=='Components';
        });
    compType = compType || sel.id;
    sm.suspendEvents();

    compsNode.removeAll();
    detailnav.loadComponents();
    detailnav.on('componenttreeloaded', function(){
        var node = compsNode.findChildBy(function(n){
            return n.get("id") == compType;
        });
        if (node) {
            sm.select(node);
        }else {
            sm.select(compsNode.firstChild);
        }
    }, detailnav, {single: true});
    sm.resumeEvents();
}

Zenoss.env.componentrefresh = refreshComponentTreeAndGrid;
Zenoss.env.componentReloader = function(compType) {
    return function(form, action) {
        refreshComponentTreeAndGrid(compType);
    };
};

/*
Zenoss.ComponentNodeUI = Ext.extend(Zenoss.HierarchyTreeNodeUI, {
    renderElements: function(n, a, targetNode, bulkRender) {
        a.text.text = Zenoss.component.displayName(a.text.text)[1]; // [1] is plural
        Zenoss.ComponentNodeUI.superclass.renderElements.apply(this, arguments);
    }
});
*/

Zenoss.nav.register({
    Device: [{
        id: 'device_overview',
        nodeType: 'subselect',
        text: _t('Overview')
    },{
        id: 'device_events',
        nodeType: 'subselect',
        text: _t('Events')
    },{
        id: UID,
        nodeType: 'async',
        text: _t('Components'),
        // hide the node; show it only when it's determined we have components
        hidden: true,
        expanded: true,
        leaf: false,
        listeners: {
            beforeclick: function(node, e) {
                node.firstChild.select();
            },
            beforeappend: function(tree, me, node){
                node.data.action = function(node, target) {
                    target.layout.setActiveItem('component_card');
                    target.layout.activeItem.setContext(UID, node.get('id'));
                };
            },
            load: function(node) {
                var card = Ext.getCmp('component_card'),
                    tbar = card.getGridToolbar();
                if (node.hasChildNodes()) {
                    node.ui.show();
                    if (tbar) {
                        tbar.show();
                    }
                } else {
                    node.ui.hide();
                    if (tbar){
                        tbar.hide();
                    }
                    card.detailcontainer.removeAll();
                    try {
                        // This can fail if the device has no components at
                        // all, but it fails deep in Ext. Also it's irrelevant
                        // in that case, so just fail quietly.
                        card.componentnav.reset();
                    } catch(e) {}
                }
            }
        },
        action: function(node, target) {
            var child = node.firstChild;
            if (!child) {
                node.on('append', function(tree,me,n){
                    selectOnRender(n, tree.getSelectionModel());
                }, node, {single:true});
            } else {
                selectOnRender(child, target.treepanel.getSelectionModel());
            }
        },
        loader: new Ext.tree.TreeLoader({
            /*
            baseAttrs: {
                uiProvider: Zenoss.ComponentNodeUI
            },
            */
            listeners: {
                load: function(loader, node, response) {
                }
            }
        })
    },{
        id: 'device_graphs',
        nodeType: 'subselect',
        text: _t('Graphs')
    },{
        id: 'device_modeler_plugins',
        nodeType: 'subselect',
        text: _t('Modeler Plugins')
    },{
        id: 'device_config_properties',
        nodeType: 'subselect',
        text: _t('Configuration Properties')
    }]
});

function componentGridOptions() {
    var grid = Ext.getCmp('component_card').componentgrid,
        sm = grid.getSelectionModel(),
        rows = sm.getSelections(),
        ranges = sm.getPendingSelections(true),
        pluck = Ext.pluck,
        uids = pluck(pluck(rows, 'data'), 'uid'),
        name = Ext.getCmp('component_searchfield').getValue();
    return {
        uids: uids,
        ranges: ranges,
        name: name,
        hashcheck: grid.lastHash
    };
}

function showMonitoringDialog() {
    var win = new Ext.Window({
        height: 115,
        width: 200,
        title: _t('Monitoring'),
        bodyStyle: 'padding:8px;padding-top:2px',
        buttonAlign: 'left',
        plain: true,
        buttons: [{
            text: _t('Submit'),
            handler: function(btn) {
                var mon = Ext.getCmp('monitoring-checkbox'),
                    opts = {
                        monitor: mon.getValue()
                    };
                Ext.apply(opts, componentGridOptions());
                btn.ownerCt.ownerCt.destroy();
                REMOTE.setComponentsMonitored(opts, function(r){
                    refreshComponentTreeAndGrid();
                });
            }
        },{
            text: _t('Cancel'),
            handler: function(btn){
                btn.ownerCt.ownerCt.destroy();
            }
        }],
        items: [{
            xtype: 'checkbox',
            name: 'monitor',
            submitValue: false,
            id: 'monitoring-checkbox',
            boxLabel: _t('Monitor these components'),
            checked: true
        }]
    });
    win.show();
    win.doLayout();
}

function showComponentLockingDialog() {
    function disableSendEvent() {
        var del = Ext.getCmp('lock-deletion-checkbox'),
            sendEvent = Ext.getCmp('send-event-checkbox');
        sendEvent.setDisabled(!del.getValue());
    }
    var win = new Ext.Window({
        height: 150,
        width: 300,
        title: _t('Locking'),
        bodyStyle: 'padding:8px;padding-top:2px',
        buttonAlign: 'left',
        plain: true,
        layout: 'fit',
        buttons: [{
            text: _t('Submit'),
            handler: function(btn) {
                var del = Ext.getCmp('lock-deletion-checkbox'),
                    upd = Ext.getCmp('lock-updates-checkbox'),
                    send = Ext.getCmp('send-event-checkbox'),
                    opts = {
                        deletion: del.getValue(),
                        updates: upd.getValue(),
                        sendEvent: send.getValue()
                    };
                Ext.apply(opts, componentGridOptions());
                btn.ownerCt.ownerCt.destroy();
                REMOTE.lockComponents(opts, function(r){
                    refreshComponentTreeAndGrid();
                });
            }
        },{
            text: _t('Cancel'),
            handler: function(btn){
                btn.ownerCt.ownerCt.destroy();
            }
        }],
        items: [{
            xtype: 'container',
            frame: false,
            layout: 'vbox',
            defaults: {
                xtype: 'checkbox',
                flex: 1,
                align: 'stretch'
            },
            id: 'lockingchecks',
            items: [{
                name: 'updates',
                submitValue: false,
                id: 'lock-updates-checkbox',
                boxLabel: _t('Lock from updates'),
                handler: disableSendEvent.createInterceptor(function(){
                    var del = Ext.getCmp('lock-deletion-checkbox');
                    if (this.getValue()) {
                        del.setValue(true);
                        del.disable();
                    } else {
                        del.enable();
                    }
                })
            },{
                name: 'deletion',
                submitValue: false,
                id: 'lock-deletion-checkbox',
                boxLabel: _t('Lock from deletion'),
                handler: disableSendEvent
            },{
                name: 'sendEventWhenBlocked',
                id: 'send-event-checkbox',
                boxLabel: _t('Send an event when an action is blocked'),
                disabled: true
            }]
        }]
    });
    win.show();
    win.doLayout();
}

var componentCard = {
    xtype: 'componentpanel',
    id: 'component_card',
    gridtbar: [{
        xtype: 'tbtext',
        id: 'component_type_label',
        style: 'font-size:10pt;font-weight:bold'
    },'-',{
        iconCls: 'customize',
        disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
        menu: [{
            text: _t('Locking...'),
            handler: showComponentLockingDialog
        },{
            id: 'component_monitor_menu_item',
            text: _t('Monitoring...'),
            handler: showMonitoringDialog
        }]
    },{
        iconCls: 'delete',
        disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
        handler: function() {
            Ext.Msg.show({
                title: _t('Delete Components'),
                msg: _t("Are you sure you want to delete these components?"),
                buttons: Ext.Msg.YESNO,
                fn: function(btn) {
                    if (btn=="yes") {
                        REMOTE.deleteComponents(componentGridOptions(), function(){
                            refreshComponentTreeAndGrid();
                        });
                    } else {
                        Ext.Msg.hide();
                    }
                }
            });
        }
    },{
        text: _t('Select'),
        disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
        menu: [{
            text: _t('All'),
            handler: function(){
                var grid = Ext.getCmp('component_card').componentgrid;
                grid.getSelectionModel().selectRange(0, grid.store.totalLength);
            }
        },{
            text: _t('None'),
            handler: function(){
                var grid = Ext.getCmp('component_card').componentgrid;
                grid.getSelectionModel().clearSelections();
            }
        }]
    }, '->', {
        xtype: 'panel',
        baseCls: 'no-panel-class',
        ui: 'none',
        width: 175,
        items: [{
                    xtype: 'searchfield',
                    id: 'component_searchfield',
                    validateOnBlur: false,
                    emptyText: _t('Type to filter...'),
                    enableKeyEvents: true,
                    filterGrid: function() {
                        var value = this.getValue();
                        if (value.length >= 3 || value.length == 0) {
                            var grid = Ext.getCmp('component_card').componentgrid;
                            grid.filter(this.getValue());
                        }
                    },
                    listeners: {
                        keypress: function(field, e) {
                            if (e.getKey() === e.ENTER) {
                                field.filterGrid();
                            } else {
                                if (!this.liveSearchTask) {
                                    this.liveSearchTask = new Ext.util.DelayedTask(function() {
                                                                                       field.filterGrid();
                                                                                   });
                                }
                                // delay half a second before we filter
                                this.liveSearchTask.delay(500);
                            }

                        }
                    }
                }]

        }
              ],
    listeners: {
        contextchange: function(me, uid, type){
            Ext.getCmp('component_type_label').setText(Zenoss.component.displayName(type)[1]);
            var sf = Ext.getCmp('component_searchfield');
            sf.setRawValue(sf.emptyText);
            sf.el.addClass(sf.emptyClass);
        }
    }
};

var deviceInformation = {
    xtype: 'fieldset',
    layout: 'column',
    title: _t('Device Information'),
    defaults: {
        columnWidth: 0.5
    },
    items: [{
        layout: 'anchor',
        defaultType: 'displayfield',
        items: [{
            name: 'name',
            fieldLabel: _t('Host Name')
        },{
            xtype: 'inheritfield',
            id: 'myinheritfield',
            items: [{
                xtype: 'textfield',
                fieldLabel: 'Value'
            }]
        },{
            name: 'deviceClass',
            fieldLabel: _t('Device Class')
        },{
            name: 'groups',
            fieldLabel: _t('Custom Groups')
        },{
            name: 'systems',
            fieldLabel: _t('Systems')
        },{
            name: 'location',
            fieldLabel: _t('Location')
        },{
            name: 'locking',
            fieldLabel: _t('Locking')
        },{
            name: 'lastChanged',
            fieldLabel: _t('Last Changed')
        },{
            name: 'lastCollected',
            fieldLabel: _t('Last Collected')
        }]
    },{
        layout: 'anchor',
        items: [{
            xtype: 'editabletextarea',
            name: 'description',
            fieldLabel: _t('Description')
        },{
            xtype: 'editabletextarea',
            name: 'comments',
            fieldLabel: _t('Comments')
        },{
            xtype: 'displayfield',
            name: 'links',
            fieldLabel: _t('Links')
        }]
    }]
};

var snmpInformation = {
    xtype: 'fieldset',
    defaultType: 'displayfield',
    title: _t('SNMP Information'),
    items: [{
        name: 'snmpSysName',
        fieldLabel: _t('SNMP SysName')
    },{
        name: 'snmpContact',
        fieldLabel: _t('SNMP Contact')
    },{
        name: 'snmpLocation',
        fieldLabel: _t('SNMP Location')
    },{
        name: 'snmpAgent',
        fieldLabel: _t('SNMP Agent')
    }]
};

var hwosInformation = {
    xtype: 'fieldset',
    defaultType: 'displayfield',
    title: _t('Hardware/OS Information'),
    items: [{
        name: 'hwManufacturer',
        fieldLabel: _t('Hardware Manufacturer')
    },{
        name: 'hwModel',
        fieldLabel: _t('Hardware Model')
    },{
        name: 'osManufacturer',
        fieldLabel: _t('OS Manufacturer')
    },{
        name: 'osModel',
        fieldLabel: _t('OS Model')
    },{
        xtype: 'editable',
        name: 'tagNumber',
        fieldLabel: _t('Tag Number')
    },{
        xtype: 'editable',
        name: 'serialNumber',
        fieldLabel: _t('Serial Number')
    },{
        xtype: 'editable',
        name: 'rackSlot',
        fieldLabel: _t('Rack Slot')
    }]
};

var overview = {
    xtype: 'deviceoverview',
    id: 'device_overview'
};

Zenoss.EventActionManager.configure({
    onFinishAction: function() {
        Ext.getCmp('device_events').updateRows();
        Ext.getCmp('devdetailbar').refresh();
    },
    findParams: function() {
        return Ext.getCmp('device_events').getSelectionParameters();
    }
});

var event_console = Ext.create('Zenoss.EventGridPanel', {
    id: 'device_events',
    stateId: 'device_events',
    newwindowBtn: true,
    actionsMenu: false,
    commandsMenu: false,
    store: Ext.create('Zenoss.events.Store', {}),
    columns: deviceColumnDefinitions()
});

var modeler_plugins = Ext.create('Zenoss.form.ModelerPluginPanel', {
    id: 'device_modeler_plugins'
});

var configuration_properties = Ext.create('Zenoss.form.ConfigPropertyPanel', {
    id: 'device_config_properties'
});

var device_graphs = Ext.create('Zenoss.form.GraphPanel', {
    id: 'device_graphs'
});

Ext.define('Zenoss.DeviceDetailNav', {
    extend: 'Zenoss.DetailNavPanel',
    alias: ['widget.devicedetailnav'],
    constructor: function(config) {
        Ext.applyIf(config, {
            target: 'detail_card_panel',
            menuIds: ['More','Add','TopLevel','Manage'],
            listeners:{
                render: function(panel) {
                    this.setContext(UID);
                },
                navloaded: function() {
                    Ext.History.init(function(mgr){
                        Ext.History.selectByToken(mgr.getToken());
                    });
                },
                nodeloaded: function(tree, node) {
                    if (node.id==UID) {
                        // Ready to load components!
                        Ext.defer(this.loadComponents, 500, this);
                    }
                },
                scope: this
            }
        });
        this.addEvents('componenttreeloaded');
        this.callParent(arguments);
    },
    loadComponents: function() {
        var rootNode = this.treepanel.getNodeById(UID);
        Zenoss.remote.DeviceRouter.getComponentTree({uid:UID}, function(data){
            rootNode.appendChild(Ext.Array.map(data, function(d) {
                d.text = Ext.String.format("{0} <span title='{1}'>({2})</span>",
                       Zenoss.component.displayName(d.text.text)[1],
                       d.text.description, d.text.count);
                d.action = function(node, target) {
                    target.layout.setActiveItem('component_card');
                    target.layout.activeItem.setContext(UID, node.get('id'));
                };
                return d;
            }));
            var card = Ext.getCmp('component_card'),
                tbar = card.getGridToolbar();
            if (rootNode.hasChildNodes()) {
                this.treepanel.setNodeVisible(rootNode, true);
                if (tbar) {
                    tbar.show();
                }
            } else {
                this.treepanel.setNodeVisible(rootNode, false);
                if (tbar){
                    tbar.hide();
                }
                card.detailcontainer.removeAll();
                try {
                    // This can fail if the device has no components at
                    // all, but it fails deep in Ext. Also it's irrelevant
                    // in that case, so just fail quietly.
                    card.componentnav.reset();
                } catch(e) {}
            }
            var tree = this.treepanel,
                sm = tree.getSelectionModel(),
                sel = sm.getSelectedNode(),
                token = Ext.History.getToken(),
                panelid = tree.ownerCt.id;
            if (!sel && token && token.slice(0,panelid.length)==panelid) {
                var parts = token.split(Ext.History.DELIMITER),
                    type = parts[1],
                    rest = parts.slice(2).join(Ext.History.DELIMITER);
                if (type) {
                    var tosel = rootNode.findChild('id', type);
                    if (tosel) {
                        selectOnRender(tosel, sm);
                    }
                    var card = Ext.getCmp('component_card');
                    if (rest) {
                        card.selectByToken(unescape(rest));
                    }
                }
            }
            this.fireEvent('componenttreeloaded');
        }, this);
    },
    filterNav: function(navpanel, config){
        //nav items to be excluded
        var excluded = [
            'status',
            'os',
            'graphs',
            'edit',
            'collectorplugins',
            'zpropertyedit',
            'events',
            'resetcommunity',
            'pushconfig',
            'modeldevice',
            'historyevents',
            'objtemplates'
        ];
        return (excluded.indexOf(config.id)==-1);
    },
    onGetNavConfig: function(contextId) {
        return Zenoss.nav.get('Device');
    },
    selectByToken: function(token) {
        var root = this.treepanel.getRootNode(),
            loader = this.treepanel.getStore(),
            sm = this.treepanel.getSelectionModel(),
            sel = sm.getSelectedNode(),
            findAndSelect = function() {
                var node = root.findChildBy(function(n){
                    return n.get('id')==token;
                });
                if (node && sel!=node) {
                    selectOnRender(node, sm);
                }
            };
        if (root.childNodes.length===0) {
            loader.on('load', findAndSelect);
        } else {
            findAndSelect();
        }
    },
    onSelectionChange: function(node) {

        var target, action, node = node[0];
        target = Ext.getCmp('detail_card_panel');
        if (!node) {
            return;
        }
        if ( node.data.action ) {
            action = node.data.action;
        } else {
            action = function(node, target) {
                var id = node.data.id;
                if (!(id in target.items.map)) {
                    var config = this.panelConfigMap[id];
                    if(config) {
                        target.add(config);
                        target.doLayout();
                    }
                }
                target.items.map[id].setContext(this.contextId);
                target.layout.setActiveItem(id);
            }.createDelegate(this);
        }
        var token = Ext.History.getToken(),
            mytoken = this.id + Ext.History.DELIMITER + node.get('id');
        if (!token || token.slice(0, mytoken.length)!=mytoken) {
            Ext.History.add(mytoken);
        }
        action(node, target);
    }

})


Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    tbar: {
        xtype: 'devdetailbar',
        id: 'devdetailbar',
        listeners: {
            render: function(me) {
                me.setContext(UID);
            },
            contextchange: function(bar, data) {
                Zenoss.env.deviceUUID = data.uuid;
            }

        }

    },
    items: [{
        region: 'west',
        split: 'true',
        ui: 'hierarchy',
        id: 'master_panel',
        width: 275,
        maxWidth: 275,
        autoScroll: true,
        items: {
            xtype: 'detailcontainer',
            ui: 'hierarchy',
            id: 'detailContainer',
            items: [{
                xtype: 'devicedetailnav',
                ui: 'hierarchy',
                id: 'deviceDetailNav'
            },{
                xtype: 'montemplatetreepanel',
                id: 'templateTree',
                ui: 'hierarchy',
                detailPanelId: 'detail_card_panel'

            }]
        }
    },{
        xtype: 'contextcardpanel',
        id: 'detail_card_panel',
        split: true,
        activeItem: 0,
        region: 'center',
        items: [overview, event_console, modeler_plugins, configuration_properties, device_graphs, componentCard]
    }]
});
Ext.getCmp('templateTree').setContext(UID);
Ext.create('Zenoss.BindTemplatesDialog', {
    id: 'bindTemplatesDialog',
    context: UID
});

Ext.create('Zenoss.ResetTemplatesDialog', {
    id: 'resetTemplatesDialog',
    context: UID
});

Ext.create('Zenoss.OverrideTemplatesDialog', {
    id: 'overrideTemplatesDialog',
    context: UID
});

Ext.create('Zenoss.AddLocalTemplatesDialog', {
    id: 'addLocalTemplatesDialog',
    context: UID
});

Ext.create('Zenoss.removeLocalTemplateDialog', {
    id: 'removeLocalTemplatesDialog',
    context: UID
});

var editDeviceClass = function(deviceClass, uid) {

    var win = new Zenoss.FormDialog({
        autoHeight: true,
        width: 400,
        title: _t('Set Device Class'),
        items: [{
            xtype: 'combo',
            name: 'deviceClass',
            fieldLabel: _t('Select a device class'),
            store: new Ext.data.DirectStore({
                directFn: Zenoss.remote.DeviceRouter.getDeviceClasses,
                root: 'deviceClasses',
                fields: ['name']
            }),
            valueField: 'name',
            width: 250,
            resizable: true,
            displayField: 'name',
            value: deviceClass,
            forceSelection: true,
            editable: false,
            autoSelect: true,
            triggerAction: 'all'
        }],
        buttons: [{
            text: _t('Save'),
            ref: '../savebtn',
            disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
            handler: function(btn) {
                var vals = btn.refOwner.editForm.getForm().getFieldValues();
                var submitVals = {
                    uids: [uid],
                    target: '/zport/dmd/Devices' + vals.deviceClass,
                    hashcheck: ''
                };
                Zenoss.remote.DeviceRouter.moveDevices(submitVals, function(data) {
                    var moveToNewDevicePage = function() {
                        var hostString = window.location.protocol + '//' +
                            window.location.host;
                        window.location = hostString + '/zport/dmd/Devices' +
                            vals.deviceClass + '/devices' +
                            uid.slice(uid.lastIndexOf('/'));
                    };
                    if (data.success) {
                        if (data.exports) {
                            Ext.Msg.show({
                                title: _t('Remodel Required'),
                                msg: _t("Not all of the configuration could be preserved, so a remodel of the device is required. Performance templates have been reset to the defaults for the device class."),
                                buttons: Ext.Msg.OK,
                                fn: moveToNewDevicePage
                            });
                        }
                        else {
                            moveToNewDevicePage();
                        }
                    }
                });
                win.destroy();
            }
        }, {
            text: _t('Cancel'),
            handler: function(btn) {
                win.destroy();
            }
        }]
    });

    win.show();
    win.doLayout();
};
function addComponentHandler(item) {
    var win = Ext.create('Zenoss.component.add.' + item.dialogId, {
        componentType: item.dialogId,
        uid: Zenoss.env.device_uid
    });
    win.show();
    win.on('destroy', function(){
        refreshComponentTreeAndGrid(win.componentType);
    });
}

Ext.getCmp('footer_bar').add([{
    xtype: 'ContextConfigureMenu',
    id: 'component-add-menu',
    iconCls: 'add',
    menuIds: [],
    listeners: {
        render: function(){
            this.setContext(UID);
        }
    },
    menuItems:[{
        text: _t('Add Ip Route Entry'),
        dialogId: 'IpRouteEntry',
        handler: addComponentHandler
    },{
        text: _t('Add Ip Interface'),
        dialogId: 'IpInterface',
        handler: addComponentHandler
    },{
        text: _t('Add OS Process'),
        dialogId: 'OSProcess',
        handler: addComponentHandler
    },{
        text: _t('Add File System'),
        dialogId: 'FileSystem',
        handler: addComponentHandler
    },{
        text: _t('Add Ip Service'),
        dialogId: 'IpService',
        handler: addComponentHandler
    },{
        text: _t('Add Win Service'),
        dialogId: 'WinService',
        handler: addComponentHandler
    }]
},{
    xtype: 'ContextConfigureMenu',
    id: 'device_configure_menu',
    listeners: {
        render: function(){
            this.setContext(UID);
        }
    },
    menuItems: [{
        xtype: 'menuitem',
        text: _t('Bind Templates'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('bindTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Add Local Template'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('addLocalTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Remove Local Template'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('removeLocalTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Reset Bindings'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('resetTemplatesDialog').show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Override Template Here'),
        hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
        handler: function(){
            Ext.getCmp('overrideTemplatesDialog').show();
        }
    },'-',{
        xtype: 'menuitem',
        text: _t('Reset/Change IP Address') + '...',
        hidden: Zenoss.Security.doesNotHavePermission('Admin Device'),
        handler: function() {
            var win = new Zenoss.FormDialog({
                title: 'Reset/Change IP Address',
                items: [{
                    xtype: 'textfield',
                    vtype: 'ipaddress',
                    name: 'ip',
                    ref: '../ipaddressfield',
                    fieldLabel: _t('IP Address (blank to use DNS)')
                }],
                buttons: [{
                    text: _t('Save'),
                    ref: '../savebtn',
                    handler: function() {
                        REMOTE.resetIp({
                            ip: this.refOwner.ipaddressfield.getValue(),
                            uids: [UID],
                            hashcheck: null
                        }, function(){
                            win.destroy();
                            Ext.getCmp('devdetailbar').setContext(UID);
                        });
                    }
                },{
                    text: _t('Cancel'),
                    handler: function(){
                        win.destroy();
                    }
                }]
            });
            win.show();
            win.doLayout();
        }
    },{
        xtype: 'menuitem',
        text: _t('Push Changes') + '...',
        hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
        handler: function() {
            Ext.Msg.show({
                title: 'Push Changes',
                msg: _t('Are you sure you want to push changes to the collectors?'),
                buttons: Ext.Msg.YESNO,
                fn: function (btnid) {
                    if (btnid!='yes') {
                        return;
                    }
                    REMOTE.pushChanges({
                        uids: [UID],
                        hashcheck: null
                    }, Ext.emptyFn);
                }
            });
        }
    },{
        xtype: 'menuitem',
        text: _t('Model Device') + '...',
        hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
        handler: function() {
            var win = new Zenoss.CommandWindow({
                uids: [UID],
                target: 'run_model',
                closeAction: 'closeAndReload',
                title: _t('Model Device')
            });
            win.show();
        }
    },{
        xtype: 'menuitem',
        text: _t('Change Device Class') + '...',
        hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
        handler: function() {
            // get the device class from the path of the device
            var uid = Zenoss.env.device_uid,
                deviceClass = uid.replace('/zport/dmd/Devices', ''),
                pieces = deviceClass.split('/');
            // remove the /devices/deviceName part
            pieces.pop();
            pieces.pop();
            editDeviceClass(pieces.join("/"), uid);
        }
    }]
},{
    id: 'commands-menu',
    text: _t('Commands'),
    hidden: Zenoss.Security.doesNotHavePermission('Run Commands'),
    listeners: {
        render: function() {
            var menu = this.menu;
            REMOTE.getUserCommands({uid:UID}, function(data){
                menu.removeAll();
                Ext.each(data, function(d){
                    menu.add({
                        text:d.id,
                        tooltip:d.description,
                        handler: function(item) {
                            var win = new Zenoss.CommandWindow({
                                uids: [UID],
                                target: UID + '/run_command',
                                command: item.text
                            });
                            win.show();
                        }
                    });
                });
            });
        }
    },
    menu: {}
}]);


});
