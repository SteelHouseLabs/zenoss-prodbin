/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

Ext.onReady(function(){

var REMOTE = Zenoss.remote.DeviceRouter,
    UID = Zenoss.env.device_uid;

var ZEvActions = Zenoss.events.EventPanelToolbarActions;

function setEventButtonsDisplayed(bool) {
    var actions = [
        ZEvActions.acknowledge,
        ZEvActions.close,
        ZEvActions.newwindow
    ];
    var method = bool ? 'show' : 'hide';
    Ext.each(actions, function(action) {
        action[method]();
    });
}

function refreshComponentTreeAndGrid(compType) {
    var tree = Ext.getCmp('deviceDetailNav').treepanel,
        sm = tree.getSelectionModel(),
        sel = sm.getSelectedNode(),
        compsNode = tree.getRootNode().findChildBy(function(n){
            return n.text=='Components';
        });
    compType = compType || sel.id;
    sm.suspendEvents();
    compsNode.reload(function(){
        sm.resumeEvents();
        var node = compsNode.findChildBy(function(n){return n.id==compType;});
        if (!node) {
            node = compsNode.firstChild;
        }
        if (!sel) {
            node.select();
        }
    });

}

Zenoss.env.componentReloader = function(compType) {
    return function(form, action) {
        refreshComponentTreeAndGrid(compType);
    };
}

Zenoss.nav.register({
    Device: [{
        id: UID,
        nodeType: 'async',
        text: _t('Components'),
        expanded: true,
        leaf: false,
        listeners: {
            beforeclick: function(node, e) {
                node.firstChild.select();
            },
            beforeappend: function(tree, me, node){
                node.attributes.action = function(node, target) {
                    target.layout.setActiveItem('component_card');
                    target.layout.activeItem.setContext(UID, node.id);
                };
            },
            load: function(node) {
                var card = Ext.getCmp('component_card'),
                    tbar = card.getGridToolbar();
                if (node.hasChildNodes()) {
                    if (tbar) {
                        tbar.show();
                    }
                } else {
                    if (tbar){
                        tbar.hide();
                    } 
                    card.detailcontainer.removeAll();
                    card.componentnav.reset();
                }
            }
        },
        action: function(node, target) {
            var child = node.firstChild;
            function selectOnRender(n) {
                if (n.rendered) {
                    n.select();
                } else {
                    n.render = n.render.createSequence(function(){
                        n.select();
                    }, n);
                }
            }
            if (!child) {
                node.on('append', function(tree,me,n){
                    selectOnRender(n);
                }, node, {single:true});
            } else {
                selectOnRender(child);
            }
        },
        loader: new Ext.tree.TreeLoader({
            directFn: Zenoss.remote.DeviceRouter.getComponentTree,
            baseAttrs: {
                uiProvider: Zenoss.HierarchyTreeNodeUI
            }
        })
    },{
        id: 'Overview',
        nodeType: 'subselect',
        text: _t('Device Overview'),
        action: function(node, target){
            target.layout.setActiveItem('device_overview');
            var panel = Ext.getCmp('devdetail_bottom_detail_panel');
            if (panel.collapsed) {
                panel.topToolbar.togglebutton.setIconClass('expand');
            } else {
                panel.topToolbar.togglebutton.setIconClass('collapse');
                setEventButtonsDisplayed(true);
            }
        }
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
        border: false,
        buttons: [{
            text: _t('Submit'),
            handler: function(btn) {
                var mon = Ext.getCmp('monitoring-checkbox'),
                    opts = {
                        monitored: mon.getValue()
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
            name: 'monitored',
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
            border: false,
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
        xtype: 'searchfield',
        id: 'component_searchfield',
        validateOnBlur: false,
        listeners: {
            valid: function(field) {
                var grid = Ext.getCmp('component_card').componentgrid;
                grid.filter(field.getValue());
            }
        }
    },'-',{
        iconCls: 'customize',
        menu: [{
            text: _t('Locking...'),
            handler: showComponentLockingDialog
        },{
            text: _t('Monitoring...'),
            handler: showMonitoringDialog
        }]
    },{
        iconCls: 'delete',
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
    }],
    listeners: {
        contextchange: function(me){
            Ext.getCmp('component_searchfield').setRawValue('');
        }
    }
};

var deviceInformation = {
    xtype: 'fieldset',
    layout: 'column',
    title: _t('Device Information'),
    defaults: {
        columnWidth: 0.5,
        border: false
    },
    items: [{
        layout: 'form',
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
        layout: 'form',
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
    id: 'device_overview',
    layout: 'border',
    border: false,
    defaults: {border:false},
    items: [{
        id: 'overview_detail_panel',
        region: 'center',
        xtype: 'form',
        border: false,
        split: true,
        autoScroll: true,
        bodyStyle: 'padding: 15px;',
        listeners: {
            render: function(){
                this.api.load(this.baseParams, function(result){
                    var systems = [], groups = [], D = result.data;
                    D.deviceClass = Zenoss.render.link(
                        D.deviceClass.uid);
                    D.location = D.location ? Zenoss.render.link(D.location.uid) : 'None';
                    Ext.each(D.systems, function(i){
                        systems.push(Zenoss.render.link(i.uid));
                    });
                    D.systems = systems.join(', ') || 'None';
                    Ext.each(D.groups, function(i){
                        groups.push(Zenoss.render.link(i.uid));
                    });
                    D.groups = groups.join(', ') || 'None';
                    if (D.locking) {
                        D.locking = Zenoss.render.locking(D.locking);
                    }
                    if (D.hwManufacturer) {
                        D.hwManufacturer = Zenoss.render.link(D.hwManufacturer.uid);
                    } else {
                        D.hwManufacturer = 'None';
                    }
                    if (D.hwModel) {
                        D.hwModel = Zenoss.render.link(D.hwModel.uid);
                    } else {
                        D.hwModel = 'None';
                    }
                    if (D.osManufacturer) {
                        D.osManufacturer = Zenoss.render.link(D.osManufacturer.uid);
                    } else {
                        D.osManufacturer = 'None';
                    }
                    if (D.osModel) {
                        D.osModel = Zenoss.render.link(D.osModel.uid);
                    } else {
                        D.osModel = 'None';
                    }
                    this.getForm().setValues(D);
                }, this);
            }
        },
        api: {
            load: REMOTE.getInfo,
            submit: REMOTE.setInfo
        },
        baseParams: {
            uid: UID
        },
        labelAlign: 'top',
        defaults:{
            anchor: Ext.isIE ? '98%' : '100%'
        },
        items: [
            deviceInformation,
            {
                border: false,
                layout: 'column',
                defaults:{
                    columnWidth: 0.5,
                    bodyStyle: 'padding:5px',
                    border: false
                },
                items: [{
                    items: hwosInformation
                },{
                    items: snmpInformation
                }]
            }
        ]
    },{
        region: 'south',
        id: 'devdetail_bottom_detail_panel',
        split: true,
        xtype: 'SimpleEventGridPanel',
        height: 250,
        listeners: {
            render: function(me) {
                me.setContext(UID);
            },
            collapse: function(me) {
                setEventButtonsDisplayed(false);
            },
            beforeexpand: function(me) {
                setEventButtonsDisplayed(true);
            }
        },
        collapsed: true,
        tbar: {
            xtype: 'consolebar',
            title: _t('Event Console'),
            items: [
                ZEvActions.acknowledge,
                ZEvActions.close,
                ZEvActions.newwindow
            ]
        },
        columns: Zenoss.env.COLUMN_DEFINITIONS
    }]
};

Zenoss.DeviceDetailNav = Ext.extend(Zenoss.DetailNavPanel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            target: 'detail_card_panel',
            menuIds: ['More','Add','TopLevel','Manage'],
            listeners:{
                render: function(panel) {
                    this.setContext(UID);
                },
                scope: this
            }
        });
        Zenoss.DeviceDetailNav.superclass.constructor.call(this, config);
    },
    filterNav: function(navpanel, config){
        //nav items to be excluded
        var excluded = [
            'status',
            'os',
            'edit',
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
        return Zenoss.nav.Device;
    },
    selectByToken: function(token) {
        var node = this.treepanel.getRootNode().findChildBy(function(n){
            return n.id==token;
        });
        if (node) {
            node.select();
        }
    },
    onSelectionChange: function(node) {
        var target, action;
        target = Ext.getCmp('detail_card_panel');
        if ( node.attributes.action ) {
            action = node.attributes.action;
        } else {
            action = function(node, target) {
                var id = node.attributes.id;
                if (!(id in target.items.map)) {
                    var config = this.panelConfigMap[id];
                    Ext.applyIf(config, {refreshOnContextChange: true});
                    if(config) {
                        target.add(config);
                        target.doLayout();
                    }
                }
                target.items.map[node.attributes.id].setContext(this.contextId);
                target.layout.setActiveItem(node.attributes.id);
            }.createDelegate(this);
        }
        Ext.History.add(this.id + Ext.History.DELIMITER + node.id);
        action(node, target);
    }
});
Ext.reg('devicedetailnav', Zenoss.DeviceDetailNav);


Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border':false
    },
    tbar: {
        xtype: 'devdetailbar',
        listeners: {
            render: function(me) {
                me.setContext(UID);
            }
        }
    },
    items: [{
        region: 'west',
        split: 'true',
        id: 'master_panel',
        width: 275,
        items: {
            xtype: 'detailcontainer',
            id: 'detailContainer',
            items: [{
                xtype: 'devicedetailnav',
                id: 'deviceDetailNav'
            }, {
                xtype: 'montemplatetreepanel',
                id: 'templateTree',
                detailPanelId: 'detail_card_panel',
                listeners: {
                    afterrender: function(me) {
                        me.setContext(UID);
                    }
                }
            }]
        }
    },{
        xtype: 'contextcardpanel',
        id: 'detail_card_panel',
        split: true,
        activeItem: 0,
        region: 'center',
        items: [componentCard, overview]
    }]
});

Ext.create({
    xtype: 'bindtemplatesdialog',
    id: 'bindTemplatesDialog',
    context: UID
});

Ext.getCmp('footer_bar').add([{
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
        handler: function(){
            Ext.getCmp('bindTemplatesDialog').show();
        }
    }]
},{
    xtype: 'ContextConfigureMenu',
    id: 'component-add-menu',
    iconCls: 'add',
    menuIds: ['IpInterface', 'WinService', 'OSProcess', 'IpService', 'FileSystem', 'IpRouteEntry'],
    listeners: {
        render: function(){
            this.setContext(UID);
        }
    }
}]);


});
