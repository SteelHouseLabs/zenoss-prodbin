/*
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
*/

(function(){

var ZC = Ext.ns('Zenoss.component'),
    ZEvActions = Zenoss.events.EventPanelToolbarActions,
    NM = ZC.nameMap = {};

ZC.registerName = function(meta_type, name, plural) {
    NM[meta_type] = [name, plural];
};

ZC.displayName = function(meta_type) {
    return NM[meta_type] || [meta_type, meta_type];
};

ZC.displayNames = function() {
    return NM;
};

function render_link(ob) {
    if (ob && ob.uid) {
        return Zenoss.render.link(ob.uid);
    } else {
        return ob;
    }
}

Zenoss.nav.register({
    Component: [{
        nodeType: 'subselect',
        id: 'Graphs',
        text: _t('Graphs'),
        action: function(node, target, combo) {
            var uid = combo.contextUid,
                cardid = uid+'_graphs',
                graphs = {
                    id: cardid,
                    xtype: 'graphpanel',
                    viewName: 'graphs',
                    showToolbar: false,
                    text: _t('Graphs')
                };
            if (!(cardid in target.items.keys)) {
                target.add(graphs);
            }
            target.layout.setActiveItem(cardid);
            target.layout.activeItem.setContext(uid);
            var tbar = target.getToolbars()[0];
            if (tbar._btns) {
                Ext.each(tbar._btns, tbar.remove, tbar);
            }
            var btns = tbar.add([
                '->',
                 {
                    xtype: 'drangeselector',
                    listeners: {
                        select: function(combo, records, index){
                            var value = records[0].data.id,
                                panel = Ext.getCmp(cardid);
                            panel.setDrange(value);
                        }
                    }
                },'-', {
                    xtype: 'button',
                    ref: '../resetBtn',
                    text: _t('Reset'),
                    handler: function(btn) {
                        Ext.getCmp(cardid).setDrange();
                    }
                },'-',{
                    xtype: 'tbtext',
                    text: _t('Link Graphs?:')
                },{
                    xtype: 'checkbox',
                    ref: '../linkGraphs',
                    checked: true,
                    listeners: {
                        check: function(chkBx, checked) {
                            var panel = Ext.getCmp(cardid);
                            panel.setLinked(checked);
                        }
                    }
                }, '-', {
                    xtype: 'graphrefreshbutton',
                    stateId: 'graphRefresh',
                    iconCls: 'refresh',
                    text: _t('Refresh'),
                    handler: function(btn) {
                        if (cardid && Ext.getCmp(cardid)) {
                            Ext.getCmp(cardid).resetSwoopies();
                        }
                    }
                }
            ]);
            tbar.doLayout();
            tbar._btns = btns;
            combo.on('select', function(c, selected){
                if (selected.id!="Graphs") {
                    Ext.each(btns, tbar.remove, tbar);
                }
            }, this, {single:true});
        }
    },{
        nodeType: 'subselect',
        id: 'Events',
        text: _t('Events'),
        action: function(node, target, combo) {
            var uid = combo.contextUid,
                cardid = uid + '_events',
                showPanel = function() {
                    target.layout.setActiveItem(cardid);
                    target.layout.activeItem.setContext(uid);
                };
            if (!(cardid in target.items.keys)) {
                var panel = target.add({
                    id: cardid,
                    xtype: 'SimpleEventGridPanel',
                    displayFilters: false,
                    stateId: 'component-event-console',
                    columns:  Zenoss.env.getColumnDefinitions(['component', 'device'])
                });
                var tbar = target.getToolbars()[0];
                if (tbar._btns) {
                    Ext.each(tbar._btns, tbar.remove, tbar);
                }
                var btns = tbar.add([
                    '-',
                    ZEvActions.acknowledge,
                    ZEvActions.close,
                    ZEvActions.refresh,
                    '-',
                    ZEvActions.newwindow
                ]);
                Ext.each(btns, function(b){b.grid = panel;});
                tbar.doLayout();
                tbar._btns = btns;
                combo.on('select', function(c, selected){
                    if (selected.id!="Events") {
                        Ext.each(btns, tbar.remove, tbar);
                    }
                }, this, {single:true});
            }
            showPanel();
        }
    },{
        nodeType: 'subselect',
        id: 'Edit',
        text: _t('Details'),
        action: function(node, target, combo) {
            var uid = combo.contextUid;
            if (!(uid in target.items.keys)) {
                Zenoss.form.getGeneratedForm(uid, function(config){
                    target.add(Ext.apply({id:uid}, config));
                    target.layout.setActiveItem(uid);
                });
            } else {
                target.layout.setActiveItem(uid);
            }
        }
    },{
        nodeType: 'subselect',
        id: 'ComponentTemplate',
        text: _t('Templates'),
        action: function(node, target, combo) {
            var uid = combo.contextUid;
            target.add(Ext.create('Zenoss.ComponentTemplatePanel',{
                ref: 'componentTemplatePanel',
                id: 'componentTemplatePanel' + uid
            }));
            target.componentTemplatePanel.setContext(uid);
            target.layout.setActiveItem('componentTemplatePanel' + uid);
        }
    }]
});

Ext.define("Zenoss.component.ComponentDetailNav", {
    alias:['widget.componentnav'],
    extend:"Zenoss.DetailNavPanel",
    constructor: function(config) {
        Ext.applyIf(config, {
            autoHeight: true,
            autoScroll: true,
            containerScroll: true,
            menuIds: []
        });
        ZC.ComponentDetailNav.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['selectionchange']);
        this.on('selectionchange', this.onSelectionChange);
    },
    onGetNavConfig: function(contextId) {
        var grid = this.ownerCt.ownerCt.ownerCt.componentgrid,
            items = [],
            monitor = false;
        Zenoss.env.GRID = grid;
        Ext.each(grid.store.data.items, function(record){
            if (record.data.monitor) { monitor = true; }
        });
        Zenoss.util.each(Zenoss.nav.get('Component'), function(item){
            if (!(item.id=='Graphs' && !monitor)) {
                items.push(item);
            }
        });
        return items;
    },
    filterNav: function(navpanel, config){
        //nav items to be excluded
        var excluded = [
            'status',
            'events',
            'resetcommunity',
            'pushconfig',
            'objtemplates',
            'modeldevice',
            'historyevents'
        ];
        return (excluded.indexOf(config.id)==-1);
    },
    onSelectionChange: function(sm, node) {
        var target = this.target || Ext.getCmp('component_detail_panel'),
            action = node.data.action || Ext.bind(function(node, target) {
                var id = node.get('id');
                if (!(id in target.items.map)) {
                    var config = this.panelConfigMap[id];
                    if(config) {
                        target.add(config);
                        target.doLayout();
                    }
                }
                target.items.map[id].setContext(this.contextId);
                target.layout.setActiveItem(id);
            }, this);
        action(node, target);
    }
});



Ext.define("Zenoss.component.ComponentPanel", {
    alias:['widget.componentpanel'],
    extend:"Ext.Panel",
    constructor: function(config) {
        var tbar = config.gridtbar,
            tbarid = Ext.id();
        if (tbar) {
            if (Ext.isArray(tbar)) {
                tbar = {items:tbar};
            }
            Ext.apply(tbar, {
                id: tbarid
            });
        }
        config = Ext.applyIf(config||{}, {
            tbarid: tbarid,
            layout: 'border',
            items: [{
                region: 'north',
                height: 250,
                split: true,
                ref: 'gridcontainer',
                tbar: tbar,
                layout: 'fit'
            },{
                xtype: 'contextcardpanel',
                region: 'center',
                ref: 'detailcontainer',
                split: true,
                tbar: {
                    cls: 'largetoolbar componenttbar',
                    height: 32,
                    items: [{
                        xtype: 'tbtext',
                        html: _t("Display: ")
                    },{
                        xtype: 'detailnavcombo',
                        menuIds: [],
                        onGetNavConfig: Ext.bind(function(uid) {
                            var grid = this.componentgrid,
                                items = [],
                                monitor = false;
                            Ext.each(grid.store.data.items, function(record){
                                if (record.data.uid==uid && record.data.monitor) {
                                    monitor = true;
                                }
                            });
                            Zenoss.util.each(Zenoss.nav.get('Component'), function(item){
                                items.push(item);
                            });
                            return items;
                        }, this),
                        filterNav: function(cfg) {
                            var excluded = [
                                'status',
                                'events',
                                'resetcommunity',
                                'pushconfig',
                                'objtemplates',
                                'template',
                                'modeldevice',
                                'historyevents'
                            ];
                            return (excluded.indexOf(cfg.id)==-1);
                        },
                        ref: '../../componentnav',
                        getTarget: Ext.bind(function() {
                            return this.detailcontainer;
                        }, this)
                    }]
                }
            }]
        });
        ZC.ComponentPanel.superclass.constructor.call(this, config);
        this.addEvents('contextchange');
    },
    getGridToolbar: function(){
        return Ext.getCmp(this.tbarid);
    },
    selectByToken: function(token) {
        if (token) {
            var grid = this.componentgrid;
            grid.selectByToken(token);
        }
    },
    setContext: function(uid, type) {
        this.contextUid = uid;
        if (type!=this.componentType) {
            this.componentType = type;

            var compType = this.componentType + 'Panel',
                xtype = Ext.ClassManager.getByAlias('widget.' + compType) ? compType : 'ComponentGridPanel';
            this.gridcontainer.removeAll();
            this.gridcontainer.add({
                xtype: xtype,
                componentType: this.componentType,
                ref: '../componentgrid',
                listeners: {
                    render: function(grid) {
                        grid.setContext(uid);
                    },
                    rangeselect: function(sm) {
                        this.detailcontainer.removeAll();
                        this.componentnav.reset();
                    },
                    selectionchange: function(sm, selected) {
                        var row = selected[0];
                        if (row) {
                            Zenoss.env.compUUID = row.data.uuid;
                            this.componentnav.setContext(row.data.uid);
                            var delimiter = Ext.History.DELIMITER,
                                token = Ext.History.getToken().split(delimiter, 2).join(delimiter);
                            Ext.History.add(token + delimiter + row.data.uid);
                            Ext.getCmp('component_monitor_menu_item').setDisabled(!row.data.usesMonitorAttribute);
                        } else {
                            this.detailcontainer.removeAll();
                            this.componentnav.reset();
                        }
                    },
                    scope: this
                }
            });
            this.gridcontainer.doLayout();
        } else {
            this.componentgrid.setContext(uid);
        }
        this.fireEvent('contextchange', this, uid, type);
    }
});


Ext.define("Zenoss.component.ComponentGridPanel", {
    alias:['widget.ComponentGridPanel'],
    extend:"Zenoss.BaseGridPanel",
    lastHash: null,
    constructor: function(config) {
        config = config || {};
        config.fields = config.fields || [{
                                            name: 'name'
                                        }, {
                                            name: 'monitored'
                                        }, {
                                            name: 'status'
                                        }, {
                                            name: 'severity'
                                        }];
        config.fields.push({name: 'uuid'});
        config.fields.push({name: 'uid'});

        // compat for autoExpandColumn
        var expandColumn = config.autoExpandColumn;
        if (expandColumn && config.columns) {
            Ext.each(config.columns, function(col){
                if (expandColumn == col.id) {
                    col.flex = 1;
                }
            });
        }

        var modelId = Ext.id(),
            model = Ext.define(modelId, {
                extend: 'Ext.data.Model',
                idProperty: 'uuid',
                fields: config.fields
            });
        config = Ext.applyIf(config||{}, {
            autoExpandColumn: 'name',
            bbar: {},
            store: new ZC.BaseComponentStore({
                sortInfo: config.sortInfo,
                model: modelId,
                initialSortColumn: config.initialSortColumn || 'name',
                directFn:config.directFn || Zenoss.remote.DeviceRouter.getComponents
            }),
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                flex: 1
            }, {
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 70,
                sortable: true
            }, {
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                renderer: Zenoss.render.pingStatus,
                width: 60
            }],
            selModel: new Zenoss.ExtraHooksSelectionModel({
                suppressDeselectOnSelect: true
            })
        });
        ZC.ComponentGridPanel.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['rangeselect']);
        this.store.proxy.on('load',
            function(proxy, o, options) {
                this.lastHash = o.result.hash || this.lastHash;
            },
            this);
        Zenoss.util.addLoadingMaskToGrid(this);
    },
    applyOptions: function(options){
        // apply options to all future parameters, not just this operation.
        var params = this.getStore().getProxy().extraParams;

        Ext.apply(params, {
            uid: this.contextUid,
            keys: Ext.Array.pluck(this.fields, 'name'),
            meta_type: this.componentType,
            name: this.componentName
        });
    },
    filter: function(name) {
        this.componentName = name;
        this.refresh();
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.getStore().on('load', function(){
            var token = Ext.History.getToken();
            if (token.split(Ext.History.DELIMITER).length!=3) {
                this.getSelectionModel().selectRange(0, 0);
                // Ext, for some reason, doesn't fire selectionchange at this
                // point, so we'll do it ourselves.
                this.fireEvent('selectionchange', this, this.getSelectionModel().getSelection());
            }
        }, this, {single:true});
        this.callParent(arguments);
    },
    selectByToken: function(uid) {
        var store = this.getStore(),
            selectionModel = this.getSelectionModel(),
            view = this.getView(),
            me = this,
            selectToken = function() {
                var found = false, i=0;
                store.each(function(r){
                    if (r.get("uid") == uid) {
                        selectionModel.select(r);
                        view.focusRow(r.index);
                        found = true;
                        return false;
                    }
                    i++;
                    return true;
                });
                if (!found) {
                    var o = {componentUid:uid};
                    Ext.apply(o, store.getProxy().extraParams);
                    Zenoss.remote.DeviceRouter.findComponentIndex(o, function(r){
                        // will return a null if not found
                        if (Ext.isNumeric(r.index)) {
                            // scroll to the correct location which will fire the guaranteedrange event
                            // and select the correct r in the above code
                            store.on('guaranteedrange', selectToken, this, {single: true});
                            var scroller = me.down('paginggridscroller');
                            if (scroller) {
                                scroller.scrollByDeltaY(scroller.rowHeight * r.index);
                            }
                        }
                    });
                }
        };

        if (!store.loaded) {
            store.on('guaranteedrange', selectToken, this, {single: true});
        } else {
            selectToken();
        }

    }
});



Ext.define("Zenoss.component.BaseComponentStore", {
    extend:"Zenoss.DirectStore",
    constructor: function(config) {
        Ext.applyIf(config, {
            pageSize: Zenoss.settings.componentGridBufferSize,
            directFn: config.directFn
        });
        ZC.BaseComponentStore.superclass.constructor.call(this, config);
        this.on('load', function(){this.loaded = true;}, this);
    }
});


Ext.define("Zenoss.component.IpInterfacePanel", {
    alias:['widget.IpInterfacePanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpInterface',
            autoExpandColumn: 'description',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'description'},
                {name: 'ipAddressObjs'},
                {name: 'network'},//, mapping:'network.uid'},
                {name: 'macaddress'},
                {name: 'usesMonitorAttribute'},
                {name: 'operStatus'},
                {name: 'adminStatus'},
                {name: 'status'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'duplex'},
                {name: 'netmask'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 50
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('IP Interface'),
                width: 150
            },{
                id: 'ipAddresses',
                dataIndex: 'ipAddressObjs',
                header: _t('IP Addresses'),
                renderer: function(ipaddresses) {
                    var returnString = '';
                    Ext.each(ipaddresses, function(ipaddress, index) {
                        if (index > 0) returnString += ', ';
                        if (ipaddress && Ext.isObject(ipaddress) && ipaddress.netmask) {
                            var name = ipaddress.name + '/' + ipaddress.netmask;
                            returnString += Zenoss.render.link(ipaddress.uid, undefined, name);
                        }
                        else if (Ext.isString(ipaddress)) {
                            returnString += ipaddress;
                        }
                    });
                    return returnString;
                }
            },{
                id: 'description',
                dataIndex: 'description',
                header: _t('Description')
            },{
                id: 'macaddress',
                dataIndex: 'macaddress',
                header: _t('MAC Address'),
                width: 120
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Monitored'),
                renderer: Zenoss.render.pingStatus,
                width: 80
            },{
                id: 'operStatus',
                dataIndex: 'operStatus',
                header: _t('Operational Status'),
                width: 110
            },{
                id: 'adminStatus',
                dataIndex: 'adminStatus',
                header: _t('Admin Status'),
                width: 80
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                width: 72,
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpInterfacePanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('IpInterface', _t('Interface'), _t('Interfaces'));

Ext.define("Zenoss.component.WinServicePanel", {
    alias:['widget.WinServicePanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'WinService',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'status'},
                {name: 'name'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'caption'},
                {name: 'startMode'},
                {name: 'startName'},
                {name: 'serviceClassUid'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Service Name'),
                renderer: Zenoss.render.WinServiceClass
            },{
                id: 'caption',
                dataIndex: 'caption',
                header: _t('Caption')
            },{
                id: 'startMode',
                dataIndex: 'startMode',
                header: _t('Start Mode')
            },{
                id: 'startName',
                dataIndex: 'startName',
                header: _t('Start Name')
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                renderer: Zenoss.render.pingStatus,
                width: 60
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.WinServicePanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('WinService', _t('Windows Service'), _t('Windows Services'));


Ext.define("Zenoss.component.IpRouteEntryPanel", {
    alias:['widget.IpRouteEntryPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpRouteEntry',
            autoExpandColumn: 'destination',
            fields: [
                {name: 'uid'},
                {name: 'destination'},
                {name: 'nextHop'},
                {name: 'id'}, // needed for nextHop link
                {name: 'device'}, // needed for nextHop link
                {name: 'interface'},
                {name: 'protocol'},
                {name: 'type'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'destination',
                dataIndex: 'destination',
                header: _t('Destination'),
                renderer: render_link
            },{
                id: 'nextHop',
                dataIndex: 'nextHop',
                header: _t('Next Hop'),
                renderer: Zenoss.render.nextHop,
                width: 250
            },{
                id: 'interface',
                dataIndex: 'interface',
                header: _t('Interface'),
                renderer: render_link
            },{
                id: 'protocol',
                dataIndex: 'protocol',
                header: _t('Protocol')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type'),
                width: 50
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpRouteEntryPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('IpRouteEntry', _t('Network Route'), _t('Network Routes'));

Ext.define("Zenoss.component.IpServicePanel", {
    alias:['widget.IpServicePanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpService',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'protocol'},
                {name: 'description'},
                {name: 'ipaddresses'},
                {name: 'port'},
                {name: 'serviceClassUid'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                renderer: Zenoss.render.IpServiceClass
            },{
                id: 'protocol',
                dataIndex: 'protocol',
                header: _t('Protocol')
            },{
                id: 'port',
                dataIndex: 'port',
                header: _t('Port')
            },{
                id: 'ipaddresses',
                dataIndex: 'ipaddresses',
                header: _t('IPs'),
                renderer: function(ips) {
                    return ips.join(', ');
                }
            },{
                id: 'description',
                dataIndex: 'description',
                header: _t('Description')
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpServicePanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('IpService', _t('IP Service'), _t('IP Services'));


Ext.define("Zenoss.component.OSProcessPanel", {
    alias:['widget.OSProcessPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'OSProcess',
            autoExpandColumn: 'processName',
            fields: [
                {name: 'uid'},
                {name: 'processName'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'processClass'},
                {name: 'alertOnRestart'},
                {name: 'failSeverity'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'processClass',
                dataIndex: 'processClass',
                header: _t('Process Class'),
                renderer: function(cls) {
                    if (cls && cls.uid) {
                        return Zenoss.render.link(cls.uid);
                    } else {
                        return cls;
                    }
                }
            },{
                id: 'processName',
                dataIndex: 'processName',
                header: _t('Name')
            },{
                id: 'alertOnRestart',
                dataIndex: 'alertOnRestart',
                renderer: Zenoss.render.checkbox,
                width: 85,
                header: _t('Restart Alert?')
            },{
                id: 'failSeverity',
                dataIndex: 'failSeverity',
                renderer: Zenoss.render.severity,
                width: 70,
                header: _t('Fail Severity')
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                width: 55,
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.OSProcessPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('OSProcess', _t('OS Process'), _t('OS Processes'));


Ext.define("Zenoss.component.FileSystemPanel", {
    alias:['widget.FileSystemPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            autoExpandColumn: 'mount',
            componentType: 'FileSystem',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'mount'},
                {name: 'totalBytes'},
                {name: 'availableBytes'},
                {name: 'usedBytes'},
                {name: 'capacityBytes'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'mount',
                dataIndex: 'mount',
                header: _t('Mount Point')
            },{
                id: 'totalBytes',
                dataIndex: 'totalBytes',
                header: _t('Total Bytes'),
                renderer: Zenoss.render.bytesString
            },{
                id: 'usedBytes',
                dataIndex: 'usedBytes',
                header: _t('Used Bytes'),
                renderer: Zenoss.render.bytesString
            },{
                id: 'availableBytes',
                dataIndex: 'availableBytes',
                header: _t('Free Bytes'),
                renderer: function(n){
                    if (n<0) {
                        return _t('Unknown');
                    } else {
                        return Zenoss.render.bytesString(n);
                    }

                }
            },{
                id: 'capacityBytes',
                dataIndex: 'capacityBytes',
                header: _t('% Util'),
                renderer: function(n) {
                    if (n=='unknown' || n<0) {
                        return _t('Unknown');
                    } else {
                        return n + '%';
                    }
                }

            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.FileSystemPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('FileSystem', _t('File System'), _t('File Systems'));


Ext.define("Zenoss.component.CPUPanel", {
    alias:['widget.CPUPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'CPU',
            autoExpandColumn: 'product',
            fields: [
                {name: 'uid'},
                {name: 'socket'},
                {name: 'manufacturer'},
                {name: 'product'},
                {name: 'clockspeed'},
                {name: 'extspeed'},
                {name: 'cacheSizeL1'},
                {name: 'cacheSizeL2'},
                {name: 'voltage'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'socket',
                dataIndex: 'socket',
                header: _t('Socket'),
                width: 45
            },{
                id: 'manufacturer',
                dataIndex: 'manufacturer',
                header: _t('Manufacturer'),
                renderer: render_link
            },{
                id: 'product',
                dataIndex: 'product',
                header: _t('Model'),
                renderer: render_link
            },{
                id: 'clockspeed',
                dataIndex: 'clockspeed',
                header: _t('Speed'),
                width: 70,
                renderer: function(x){ return x + ' MHz';}
            },{
                id: 'extspeed',
                dataIndex: 'extspeed',
                header: _t('Ext Speed'),
                width: 70,
                renderer: function(x){ return x + ' MHz';}
            },{
                id: 'cacheSizeL1',
                dataIndex: 'cacheSizeL1',
                header: _t('L1'),
                width: 70,
                renderer: function(x){ return x + ' KB';}
            },{
                id: 'cacheSizeL2',
                dataIndex: 'cacheSizeL2',
                header: _t('L2'),
                width: 70,
                renderer: function(x){ return x + ' KB';}
            },{
                id: 'voltage',
                dataIndex: 'voltage',
                header: _t('Voltage'),
                width: 70,
                renderer: function(x){ return x + ' mV';}
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.CPUPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('CPU', _t('Processor'), _t('Processors'));


Ext.define("Zenoss.component.ExpansionCardPanel", {
    alias:['widget.ExpansionCardPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'ExpansionCard',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'slot'},
                {name: 'name'},
                {name: 'serialNumber'},
                {name: 'manufacturer'},
                {name: 'product'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'slot',
                dataIndex: 'slot',
                header: _t('Slot'),
                width: 80
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'serialNumber',
                dataIndex: 'serialNumber',
                header: _t('Serial Number'),
                width: 110
            },{
                id: 'manufacturer',
                dataIndex: 'manufacturer',
                header: _t('Manufacturer'),
                renderer: render_link,
                width: 110
            },{
                id: 'product',
                dataIndex: 'product',
                header: _t('Model'),
                renderer: render_link,
                width: 130
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.ExpansionCardPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('ExpansionCard', _t('Card'), _t('Cards'));


Ext.define("Zenoss.component.PowerSupplyPanel", {
    alias:['widget.PowerSupplyPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'PowerSupply',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'watts'},
                {name: 'type'},
                {name: 'state'},
                {name: 'millivolts'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'watts',
                dataIndex: 'watts',
                header: _t('Watts')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'millivolts',
                dataIndex: 'millivolts',
                header: _t('Millivolts')
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.PowerSupplyPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('PowerSupply', _t('Power Supply'), _t('Power Supplies'));


Ext.define("Zenoss.component.TemperatureSensorPanel", {
    alias:['widget.TemperatureSensorPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'TemperatureSensor',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'state'},
                {name: 'temperature'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'temperature',
                dataIndex: 'temperature',
                header: _t('Temperature'),
                renderer: function(x) {
                    if (x == null) {
                        return "";
                    } else {
                        return x + " F";
                    }
                }
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.TemperatureSensorPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('TemperatureSensor', _t('Temperature Sensor'), _t('Temperature Sensors'));


Ext.define("Zenoss.component.FanPanel", {
    alias:['widget.FanPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'Fan',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'state'},
                {name: 'type'},
                {name: 'rpm'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type')
            },{
                id: 'rpm',
                dataIndex: 'rpm',
                header: _t('RPM')
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.FanPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('Fan', _t('Fan'), _t('Fans'));

})();
