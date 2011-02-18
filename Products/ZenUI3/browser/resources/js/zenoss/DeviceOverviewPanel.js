(function(){

    var REMOTE = Zenoss.remote.DeviceRouter;

    var resetCombo = function(combo, manufacturer) {
        combo.clearValue();
        combo.getStore().setBaseParam('manufacturer', manufacturer);
        delete combo.lastQuery;
        //combo.doQuery(combo.allQuery, true);
    };

    var clickToEditConfig = function(obj) {
        return {
            constructor: function(config) {
                var editLink = '<a href="javascript:" class="manu-edit-link">'+
                                _t('Edit') + '</a>';
                config.fieldLabel += editLink;
                config.listeners = Ext.apply(config.listeners||{}, {
                    render: function(p) {
                        p.editlink = p.label.select('a.manu-edit-link');
                        p.editlink.on('click', function(){
                            p.fireEvent('labelclick', p);
                        }, p);
                    }
                });
                obj.superclass.constructor.call(this, config);
                this.addEvents('labelclick');
            }
        }
    }
    
    var ClickToEditField = Ext.extend(Zenoss.form.LinkField, {});
    ClickToEditField = Ext.extend(Zenoss.form.LinkField,
                                  clickToEditConfig(ClickToEditField));
    Ext.reg('clicktoedit', ClickToEditField);
    
    var ClickToEditNoLink = Ext.extend(Ext.form.DisplayField, {});
    ClickToEditNoLink = Ext.extend(Ext.form.DisplayField,
                                   clickToEditConfig(ClickToEditNoLink));
    Ext.reg('clicktoeditnolink', ClickToEditNoLink);
    

    function editManuInfo (vals, uid) {
        function name(uid) {
            if (!uid){
                return 'Unknown';
            }
            if (!Ext.isString(uid)) {
                uid = uid.uid;
            }
            return uid.split('/').reverse()[0];
        }

        var FIELDWIDTH = 300;

        var hwManufacturers = {
            xtype: 'manufacturercombo',
            width: FIELDWIDTH,
            name: 'hwManufacturer',
            fieldLabel: _t('HW Manufacturer'),
            value: name(vals.hwManufacturer),
            listeners: {'select': function(combo, record, index){
                var productCombo = Ext.getCmp('hwproductcombo');
                resetCombo(productCombo, record.data.name);
            }}
        };

        var hwProduct = {
            xtype: 'productcombo',
            prodType: 'HW',
            width: FIELDWIDTH,
            value: name(vals.hwModel),
            resizable: true,
            name: 'hwProductName',
            fieldLabel: _t('HW Product'),
            id: 'hwproductcombo'
        };

        var osManufacturers = {
            xtype: 'manufacturercombo',
            width: FIELDWIDTH,
            name: 'osManufacturer',
            value: name(vals.osManufacturer),
            fieldLabel: _t('OS Manufacturer'),
            listeners: {'select': function(combo, record, index){
                var productCombo = Ext.getCmp('osproductcombo');
                resetCombo(productCombo, record.data.name);
            }}
        };

        var osProduct = {
            xtype: 'productcombo',
            prodType: 'OS',
            width: FIELDWIDTH,
            value: name(vals.osModel),
            resizable: true,
            name: 'osProductName',
            id: 'osproductcombo',
            fieldLabel: _t('OS Product')
        };

        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 390,
            title: _t('Edit Manufacturer Info'),
            items: [{
                xtype: 'container',
                layout: 'form',
                autoHeight: true,
                style: 'padding-bottom:5px;margin-bottom:5px;border-bottom:1px solid #555;',
                items: [hwManufacturers, hwProduct]
            },{
                xtype: 'container',
                layout: 'form',
                autoHeight: true,
                items: [osManufacturers, osProduct]
            }],
            buttons: [{
                text: _t('Save'),
                ref: '../savebtn',
                disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                handler: function(btn){
                    var vals = btn.refOwner.editForm.getForm().getFieldValues();
                    Ext.apply(vals, {uid:uid});
                    REMOTE.setProductInfo(vals, function(r) {
                        Ext.getCmp('device_overview').load();
                        win.destroy();
                    });
                }
            },{
                text: _t('Cancel'),
                handler: function(btn){
                    win.destroy();
                }
            }]
        });
        win.show();
        win.doLayout();
    }
    
    var editDeviceClass = function(values, uid) {
        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 300,
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
                displayField: 'name',
                value: values.deviceClass.uid.slice(18),
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
                            hostString = window.location.protocol + '//' +
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
    
    Zenoss.remote.DeviceRouter.getCollectors({}, function(d){
        var collectors = [];
        Ext.each(d, function(r){collectors.push([r]);});
        Zenoss.env.COLLECTORS = collectors;
    });
    
    var editCollector = function(values, uid) {
        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 300,
            title: _t('Set Collector'),
            items: [{
                xtype: 'combo',
                name: 'collector',
                fieldLabel: _t('Select a collector'),
                mode: 'local',
                store: new Ext.data.ArrayStore({
                    data: Zenoss.env.COLLECTORS,
                    fields: ['name']
                }),
                valueField: 'name',
                displayField: 'name',
                value: values.collector,
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
                        collector: vals.collector,
                        hashcheck: ''
                    };
                    Zenoss.remote.DeviceRouter.setCollector(submitVals, function(data) {
                        Ext.getCmp('device_overview').load();
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
    
    var editGroups = function(currentGroups, uid, config) {
        var win = new Zenoss.FormDialog({
            width: 350,
            height: 150,
            title: config.title,
            items: [{
                xtype: 'panel',
                html: config.instructions
            }, {
                xtype: 'spacer',
                height: 5
            }, {
                xtype: 'panel',
                layout: 'hbox',
                width: '100%',
                items: [{
                    xtype: 'combo',
                    ref: '../../selectgroup',
                    name: 'group',
                    store: new Ext.data.DirectStore({
                        directFn: config.getGroupFn,
                        root: config.getGroupRoot,
                        fields: ['name']
                    }),
                    valueField: 'name',
                    displayField: 'name',
                    forceSelection: true,
                    editable: false,
                    autoSelect: true,
                    triggerAction: 'all',
                    flex: 4
                }, {
                    xtype: 'button',
                    ref: '../../addgroupbutton',
                    text: _t('Add'),
                    handler: function(btn) {
                        var selectedGroup = btn.refOwner.selectgroup.getValue();
                        if (selectedGroup) {
                            btn.refOwner.grouplist.addGroup(selectedGroup);
                        }
                    },
                    flex: 1
                }]
            }, {
                xtype: 'panel',
                ref: '../grouplist',
                addGroup: function(group, displayOnly) {
                    if (group in this.groups) {
                        if (this.groups[group] == 'del')
                            this.groups[group] = '';
                        else
                            return;
                    }
                    else {
                        this.groups[group] = displayOnly ? '' : 'add';
                    }
                    
                    var grouplist = this;
                    var oldHeight = this.getHeight();
                    this.add({xtype: 'spacer', height: 5});
                    this.add({
                        xtype: 'panel',
                        layout: 'hbox',
                        width: '100%',
                        layoutConfig: {
                            align:'middle'
                        },
                        items: [{
                            xtype: 'panel',
                            html: group
                        }, {
                            xtype: 'spacer',
                            flex: 1
                        }, {
                            xtype: 'button',
                            text: _t('Remove'),
                            ref: 'delbutton',
                            group: group,
                            handler: function(btn) {
                                grouplist.delGroup(group, btn.refOwner);
                            }
                        }]
                    });
                    this.bubble(function() {this.doLayout();});
                    
                    if (displayOnly) return;
                    win.setHeight(win.getHeight() + this.getHeight() - oldHeight);
                },
                delGroup: function(group, panel) {
                    if (this.groups[group] == 'add')
                        delete this.groups[group];
                    else
                        this.groups[group] = 'del';
                    
                    var oldHeight = this.getHeight();
                    panel.destroy();
                    this.bubble(function() {this.doLayout();});
                    win.setHeight(win.getHeight() + this.getHeight() - oldHeight);
                },
                groups: {},
                listeners: {
                    render: function(thisPanel) {
                        Ext.each(currentGroups, function(group){
                            thisPanel.addGroup(group.uid.slice(config.dmdPrefix.length), true);
                        });
                    }
                }
            }],
            buttons: [{
                text: _t('Save'),
                ref: '../savebtn',
                disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                handler: function(btn) {
                    Ext.iterate(btn.refOwner.grouplist.groups, function(group, op) {
                        var submitVals = {
                            uids: [uid],
                            hashcheck: ''
                        };
                        
                        if (op == 'del') {
                            submitVals['uid'] = config.dmdPrefix + group;
                            Zenoss.remote.DeviceRouter.removeDevices(submitVals, function(data) {
                                Ext.getCmp('device_overview').load();
                            });
                        }
                        if (op == 'add') {
                            submitVals['target'] = config.dmdPrefix + group;
                            Zenoss.remote.DeviceRouter.moveDevices(submitVals, function(data) {
                                Ext.getCmp('device_overview').load();
                            });
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
        win.setHeight(win.getHeight() + win.grouplist.getHeight());
    };
    
    var editLocation = function(values, uid) {
        var win = new Zenoss.FormDialog({
            autoHeight: true,
            width: 300,
            title: _t('Set Location'),
            items: [{
                xtype: 'combo',
                name: 'location',
                fieldLabel: _t('Select a location'),
                store: new Ext.data.DirectStore({
                    directFn: Zenoss.remote.DeviceRouter.getLocations,
                    root: 'locations',
                    fields: ['name']
                }),
                valueField: 'name',
                displayField: 'name',
                value: values.location ? values.location.uid.slice(20) : '',
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
                    
                    if (vals.location) {
                        var submitVals = {
                            uids: [uid],
                            target: '/zport/dmd/Locations' + vals.location,
                            hashcheck: ''
                        };
                        Zenoss.remote.DeviceRouter.moveDevices(submitVals, function(data) {
                            if (data.success) {
                                Ext.getCmp('device_overview').load();
                            }
                        });
                    }
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


    function isField(c) {
        return !!c.setValue && !!c.getValue && !!c.markInvalid && !!c.clearInvalid;
    }

    Zenoss.DeviceOverviewForm = Ext.extend(Ext.form.FormPanel, {
        labelAlign: 'top',
        paramsAsHash: true,
        frame: true,
        defaults: {
            labelStyle: 'font-size: 13px; color: #5a5a5a',
            anchor: '100%'
        },
        buttonAlign: 'left',
        buttons: [{
            text: _t('Save'),
            ref: '../savebtn',
            disabled: true,
            hidden: true,
            handler: function(btn){
                this.refOwner.getForm().submit();
            }
        },{
            text: _t('Cancel'),
            ref: '../cancelbtn',
            disabled: true,
            hidden: true,
            handler: function() {
                this.refOwner.getForm().reset();
            }
        }],
        cls: 'device-overview-form-wrapper',
        bodyCssClass: 'device-overview-form',
        listeners: {
            'add': function(me, field, index){
                if (isField(field)) {
                    this.onFieldAdd.call(this, field);
                }
            }
        },
        constructor: function(config) {
            config = Ext.applyIf(config || {}, {
                trackResetOnLoad: true
            });
            config.listeners = Ext.applyIf(config.listeners||{}, this.listeners);
            Zenoss.DeviceOverviewForm.superclass.constructor.call(this, config);
        },
        showButtons: function() {
            if (!this.rendered) {
                this.on('render', this.showButtons, this);
            } else {
                this.savebtn.show();
                this.cancelbtn.show();
            }
        },
        doButtons: function() {
            this.setButtonsDisabled(!this.form.isDirty());
        },
        setButtonsDisabled: function(b) {
            if (Zenoss.Security.hasPermission('Manage Device')) {
                this.savebtn.setDisabled(b);
            }
            this.cancelbtn.setDisabled(b);  
        },
        onFieldAdd: function(field) {
            if (!field.isXType('displayfield')) {
                this.showButtons();
                this.mon(field, 'valid', this.doButtons, this);
            }
        },
        hideFooter: function() {
            this.footer.hide();
        },
        showFooter: function() {
            this.footer.show();
        },
        addField: function(field) {
            this.items.push( field );
        },
        addFieldAfter: function(field, afterFieldName) {
            this.items.splice(this._indexOfFieldName(afterFieldName)+1, 0, field);
        },
        _indexOfFieldName: function(name) {
            var idx = -1
            for ( i = 0; i < this.items.length; i++ ){
                if (this.items[i].name == name){
                    idx = i
                    break
                }
            }
        return idx
        },
        replaceField: function(name,field) {
            idx = this._indexOfFieldName(name)
            this.items[idx] = field
        },
        removeField: function(name) {
            idx = this._indexOfFieldName(name)
            this.items.splice(idx,1)
        },
        getField: function(name) {
            return this.items[this._indexOfFieldName(name)]
        }

    });

    Ext.reg('devformpanel', Zenoss.DeviceOverviewForm);

    Zenoss.DeviceOverviewPanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                autoScroll: true,
                bodyCssClass: 'device-overview-panel',
                padding: '10',
                border: false,
                frame: false,
                defaults: {
                    border: false
                },
                forms: [],
                listeners: {
                    add: function(item) {
                        if (item.isXType('form')) {
                            var f = item.getForm();
                            f.api = this.api;
                            f.baseParams = this.baseParams;
                            this.forms.push(item);
                        }
                    }
                },
                items: [{
                    layout: 'hbox',
                    defaults: {
                        flex: 1
                    },
                    layoutConfig: {
                        align: 'stretchmax',
                        defaultMargins: '10'
                    },
                    defaultType: 'devformpanel',
                    items: [{
                        id:'deviceoverviewpanel_summary',
                        defaultType: 'displayfield',
                        items: [{
                            fieldLabel: _t('Uptime'),
                            name: 'uptime'
                        },{
                            fieldLabel: _t('First Seen'),
                            name: 'firstSeen'
                        },{
                            fieldLabel: _t('Last Change'),
                            name: 'lastChanged'
                        },{
                            fieldLabel: _t('Model Time'),
                            name: 'lastCollected'
                        },{
                            fieldLabel: _t('Locking'),
                            name: 'locking'
                        },{
                            xtype: 'displayfield',
                            name: 'memory',
                            fieldLabel: _t('Memory/Swap')
                        }]
                    },{
                        id:'deviceoverviewpanel_idsummary',
                        defaultType: 'displayfield',
                        autoHeight: true,
                        listeners: {
                            actioncomplete: function(form, action) {
                                if (action.type=='directsubmit') {
                                    var bar = Ext.getCmp('devdetailbar');
                                    if (bar) {
                                        bar.refresh();
                                    }
                                }
                            }
                        },
                        items: [{
                            xtype: 'textfield',
                            name: 'name',
                            fieldLabel: _t('Device Name')
                        },{
                            xtype: 'ProductionStateCombo',
                            fieldLabel: _t('Production State'),
                            name: 'productionState'
                        },{
                            xtype: 'PriorityCombo',
                            fieldLabel: _t('Priority'),
                            name: 'priority'
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editDeviceClass(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            fieldLabel: _t('Device Class'),
                            name: 'deviceClass'
                        },{
                            xtype: 'clicktoeditnolink',
                            listeners: {
                                labelclick: function(p){
                                    editCollector(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            fieldLabel: _t('Collector'),
                            name: 'collector'
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editGroups(this.getValues().systems, this.contextUid, {
                                        title: _t('Set Systems'),
                                        instructions: _t('Add/Remove systems'),
                                        getGroupFn: Zenoss.remote.DeviceRouter.getSystems,
                                        getGroupRoot: 'systems',
                                        dmdPrefix: '/zport/dmd/Systems'
                                    });
                                },
                                scope: this
                            },
                            fieldLabel: _t('Systems'),
                            name: 'systems'
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editGroups(this.getValues().groups, this.contextUid, {
                                        title: _t('Set Groups'),
                                        instructions: _t('Add/Remove groups'),
                                        getGroupFn: Zenoss.remote.DeviceRouter.getGroups,
                                        getGroupRoot: 'groups',
                                        dmdPrefix: '/zport/dmd/Groups'
                                    });
                                },
                                scope: this
                            },
                            fieldLabel: _t('Groups'),
                            name: 'groups'
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editLocation(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            fieldLabel: _t('Location'),
                            name: 'location'
                        }]
                    },{
                        id:'deviceoverviewpanel_descriptionsummary',
                        defaultType: 'textfield',
                        items: [{
                            fieldLabel: _t('Tag'),
                            name: 'tagNumber'
                        },{
                            fieldLabel: _t('Serial Number'),
                            name: 'serialNumber'
                        },{
                            fieldLabel: _t('Rack Slot'),
                            name: 'rackSlot'
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'hwManufacturer',
                            fieldLabel: _t('Hardware Manufacturer')
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'hwModel',
                            fieldLabel: _t('Hardware Model')
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'osManufacturer',
                            fieldLabel: _t('OS Manufacturer')
                        },{
                            xtype: 'clicktoedit',
                            listeners: {
                                labelclick: function(p){
                                    editManuInfo(this.getValues(), this.contextUid);
                                },
                                scope: this
                            },
                            name: 'osModel',
                            fieldLabel: _t('OS Model') 
                        }]
                    }]
                },{
                    id:'deviceoverviewpanel_customsummary',
                    defaultType: 'devformpanel',
                    autoHeight: true,
                    layout: 'hbox',
                    layoutConfig: {
                        align: 'stretchmax',
                        defaultMargins: '10'
                    },
                    items: [{
                        defaultType: 'displayfield',
                        flex: 2,
                        items: [{
                            fieldLabel: _t('Links'),
                            name: 'links'
                        },{
                            xtype: 'textarea',
                            grow: true,
                            fieldLabel: _t('Comments'),
                            name: 'comments'
                        }]
                    },{
                    id:'deviceoverviewpanel_snmpsummary',
                        defaultType: 'displayfield',
                        flex: 1,
                        minHeight: 230,
                        items: [{
                            fieldLabel: _t('SNMP SysName'),
                            name: 'snmpSysName'
                        },{
                            fieldLabel: _t('SNMP Location'),
                            name: 'snmpLocation'
                        },{
                            fieldLabel: _t('SNMP Contact'),
                            name: 'snmpContact'
                        },{
                            fieldLabel: _t('SNMP Agent'),
                            name: 'snmpAgent'
                        }]
                    }]
                }]
            });
            Zenoss.DeviceOverviewPanel.superclass.constructor.call(this, config);
        },
        api: {
            load: REMOTE.getInfo,
            submit: function(form, success, scope) {
                var o = {},
                    vals = scope.form.getFieldValues(true);
                Ext.apply(o, vals, success.params);
                REMOTE.setInfo(o, function(result){
                    this.form.clearInvalid();
                    this.form.setValues(vals);
                    this.form.afterAction(this, true);
                    this.form.reset();
                }, scope);
            }
        },
        baseParams: {},
        setContext: function(uid) {
            this.contextUid = uid;
            this.baseParams.uid = uid;
            this.load();
        },
        getFieldNames: function() {
            var keys = [];
            Ext.each(this.forms, function(f){
                for (var key in f.getForm().getFieldValues(false)) {
                    if (keys.indexOf(key)==-1) {
                        keys.push(key);
                    }
                }
            });
            return keys;
        },
        load: function() {
            var o = Ext.apply({keys:this.getFieldNames()}, this.baseParams);
            this.api.load(o, function(result) {
                var systems = [], groups = [], D = result.data;
                if (D.locking) {
                    D.locking = Zenoss.render.locking(D.locking);
                }
                if (D.memory) {
                    D.memory = D.memory.ram + '/' + D.memory.swap;
                } else {
                    D.memory = 'Unknown/Unknown';
                }
                this.setValues(D);
                this.doLayout();
            }, this);
        },
        getValues: function() {
            var o = {};
            Ext.each(this.forms, function(form){
                Ext.apply(o, form.getForm().getFieldValues());
            }, this);
            return o;
        },
        setValues: function(d) {
            Ext.each(this.forms, function(form){
                form.getForm().setValues(d);
            });
        }
    });

    Ext.reg('deviceoverview', Zenoss.DeviceOverviewPanel);

})();
