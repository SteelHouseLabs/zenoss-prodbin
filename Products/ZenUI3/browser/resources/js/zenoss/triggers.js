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

Ext.ns('Zenoss.ui.Triggers');

Ext.onReady(function () {

    var router = Zenoss.remote.TriggersRouter,
        ZFR = Zenoss.form.rule,
        STRINGCMPS = ZFR.STRINGCOMPARISONS,
        NUMCMPS = ZFR.NUMBERCOMPARISONS,
        AddDialogue,
        addNotificationDialogue,
        addNotificationDialogueConfig,
        addScheduleDialogue,
        addScheduleDialogueConfig,
        addTriggerDialogue,
        colModel,
        colModelConfig,
        detailPanelConfig,
        displayEditTriggerDialogue,
        displayNotificationEditDialogue,
        displayScheduleEditDialogue,
        EditNotificationDialogue,
        editNotificationDialogue,
        editNotificationDialogueConfig,
        editScheduleDialogue,
        editScheduleDialogueConfig,
        editTriggerDialogue,
        EditTriggerDialogue,
        EditScheduleDialogue,
        masterPanelConfig,
        navSelectionModel,
        NotificationPageLayout,
        notificationPanelConfig,
        notificationsPanelConfig,
        NotificationSubscriptions,
        notification_panel,
        PageLayout,
        reloadNotificationGrid,
        reloadScheduleGrid,
        reloadTriggersGrid,
        SchedulesPanel,
        schedulesPanelConfig,
        schedules_panel,
        TriggersGridPanel,
        triggersPanelConfig,
        disableTabContents;


    AddDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 120,
                width: 300,
                boxMaxWidth: 300, // for chrome, safari
                modal: true,
                plain: true,
                closeAction: 'hide',
                items:{
                    xtype:'form',
                    ref: 'addForm',
                    border: false,
                    monitorValid: true,
                    buttonAlign: 'center',
                    items:[{
                        xtype: 'textfield',
                        name: 'newId',
                        ref: 'newId',
                        allowBlank: false,
                        vtype: 'alphanum',
                        fieldLabel: _t('Id')
                    }],
                    buttons:[{
                        xtype: 'button',
                        text: _t('Submit'),
                        ref: '../../submitButton',
                        formBind: true,
                        /*
                         * This dialogue is used to generically add objects for
                         * triggers, notifications and schedule windows. For
                         * triggers and notifications, do the normal thing, but
                         * for schedules, let the config pass in a handler
                         * since creating a window requires slightly different
                         * context.
                         */
                        handler: function(button) {
                            if (config.submitHandler) {
                                config.submitHandler(button);
                            } else {
                                var params = {
                                    newId: button.refOwner.addForm.newId.getValue()
                                };
                                config.directFn(params, function(){
                                    button.refOwner.addForm.newId.setValue('');
                                    config.reloadFn();
                                    button.refOwner.hide();
                                });
                            }
                        }
                    },{
                        xtype: 'button',
                        ref: '../../cancelButton',
                        text: _t('Cancel'),
                        handler: function(button) {
                            button.refOwner.hide();
                        }
                    }]}
            });
            AddDialogue.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('triggersadddialogue', AddDialogue);


    /**
     * NOTIFICATIONS
     **/

    notificationPanelConfig = {
        id: 'notification_panel',
        xtype: 'notificationsubscriptions'
    };

    schedulesPanelConfig = {
        id: 'schedules_panel',
        xtype: 'schedulespanel'
    };


    disableTabContents = function(tab) {
        // disable everything in this tab, but then re-enable the tab itself so
        // that we can still view it's contents.
        tab.cascade(function(){
            this.disable();
        });
        tab.setDisabled(false);
    };

    var enableTabContents = function(tab) {
        tab.cascade(function() {
            this.enable();
        });
        tab.setDisabled(false);
    }

    reloadNotificationGrid = function() {
        Ext.getCmp(notificationPanelConfig.id).getStore().reload();
    };


    reloadScheduleGrid = function() {
        var panel = Ext.getCmp(notificationPanelConfig.id),
            row = panel.getSelectionModel().getSelected();
        if (row) {
            Ext.getCmp(schedulesPanelConfig.id).getStore().reload({uid:row.data.uid});
        }
    };

    displayScheduleEditDialogue = function(data) {
        var dialogue = Ext.getCmp(editScheduleDialogueConfig.id);
        dialogue.loadData(data);
        dialogue.show();
    };

    editScheduleDialogueConfig = {
        id: 'edit_schedule_dialogue',
        xtype: 'editscheduledialogue',
        title: _t('Edit Notification Subscription'),
        directFn: router.updateWindow,
        reloadFn: reloadScheduleGrid
    };

    addScheduleDialogueConfig = {
        id: 'add_schedule_dialogue',
        xtype: 'addialogue',
        title: _t('Add Schedule Window'),
        directFn: router.addWindow,
        submitHandler: function(button) {
            var panel = Ext.getCmp(notificationPanelConfig.id),
                row = panel.getSelectionModel().getSelected(),
                params = {
                    newId: button.refOwner.addForm.newId.getValue(),
                    contextUid: row.data.uid
                };

            router.addWindow(params, function(){
                button.refOwner.addForm.newId.setValue('');
                button.refOwner.hide();
                reloadScheduleGrid();
            });
        }
    };


    var writeColumn = new Ext.grid.CheckColumn({
        header: _t('Write'),
        dataIndex: 'write'
    });

    var manageColumn = new Ext.grid.CheckColumn({
        header: _t('Manage'),
        dataIndex: 'manage'
    });

    var UsersPermissionGrid = Ext.extend(Ext.grid.EditorGridPanel, {
        constructor: function(config) {
            var me = this;

            config = config || {};
            this.allowManualEntry = config.allowManualEntry || false;
            Ext.applyIf(config, {
                ref: 'users_grid',
                border: false,
                viewConfig: {forceFit: true},
                title: config.title,
                autoExpandColumn: 'value',
                loadMask: {msg:_t('Loading...')},
                autoHeight: true,
                plugins: [writeColumn, manageColumn],
                keys: [
                    {
                        key: [Ext.EventObject.ENTER],
                        handler: function() {
                            me.addValueFromCombo();
                        }
                    }
                ],
                tbar: {
                    items: [
                        {
                            xtype: 'combo',
                            ref: 'users_combo',
                            typeAhead: true,
                            triggerAction: 'all',
                            lazyRender:true,
                            mode: 'local',
                            store: {
                                xtype: 'directstore',
                                directFn: router.getRecipientOptions,
                                root: 'data',
                                autoLoad: true,
                                idProperty: 'value',
                                fields: [
                                    'type',
                                    'label',
                                    'value'
                                ]
                            },
                            valueField: 'value',
                            displayField: 'label'
                        },{
                            xtype: 'button',
                            text: 'Add',
                            ref: 'add_button',
                            handler: function(btn, event) {
                                me.addValueFromCombo()
                            }
                        },{
                            xtype: 'button',
                            ref: 'delete_button',
                            iconCls: 'delete',
                            handler: function(btn, event) {
                                var row = btn.refOwner.ownerCt.getSelectionModel().getSelected();
                                btn.refOwner.ownerCt.getStore().remove(row);
                                btn.refOwner.ownerCt.getView().refresh();
                            }
                        }
                    ]
                },
                store: new Ext.data.JsonStore({
                    autoDestroy: true,
                    storeId: 'users_combo_store',
                    autoLoad: false,
                    idProperty: 'value',
                    fields: [
                        'type',
                        'label',
                        'value',
                        {name: 'write', type: 'bool'},
                        {name: 'manage', type: 'bool'}
                    ],
                    data: []
                }),
                colModel: new Ext.grid.ColumnModel({
                    defaults: {
                        width: 120,
                        sortable: true
                    },
                    columns: [
                        {
                            header: _t('Type'),
                            dataIndex: 'type'
                        },{
                            header: config.title,
                            dataIndex: 'label'
                        },
                        writeColumn,
                        manageColumn
                    ]
                }),
                sm: new Ext.grid.RowSelectionModel({singleSelect:true})
            });
            UsersPermissionGrid.superclass.constructor.apply(this, arguments);
        },
        addValueFromCombo: function() {
            var val = this.getTopToolbar().users_combo.getValue(),
                row = this.getTopToolbar().users_combo.getStore().getById(val),
                type = 'manual',
                label;

            if (row) {
                type = row.data.type;
                label = row.data.label;
            }
            else {
                val = this.getTopToolbar().users_combo.getRawValue();
                label = val;
            }


            if (!this.allowManualEntry && type == 'manual') {
                Zenoss.message.error(_t('Manual entry not permitted here.'));
            }
            else {
                var existingIndex = this.getStore().findExact('value', val);

                if (!Ext.isEmpty(val) && existingIndex == -1) {
                    var record = new Ext.data.Record({
                        type:type,
                        value:val,
                        label:label,
                        write:false,
                        manage: false
                    });
                    this.getStore().add(record);
                    this.getView().refresh();
                    this.getTopToolbar().users_combo.clearValue();
                }
            }

        },
        loadData: function(data) {
            this.getStore().loadData(data.users);
        }
    });



    var NotificationTabContent = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                padding: 20,
                unstyled: true,
                border: false,
                layout: 'form',
                autoScroll: true,
                height: 380,
                width: 500,
                defaults: {
                    width: 450
                }
            });
            NotificationTabContent.superclass.constructor.apply(this, arguments);
        }
    });

    var NotificationTabPanel = Ext.extend(Ext.TabPanel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                ref: '../tabPanel',
                activeTab: 0,
                activeIndex: 0,
                unstyled: true,
                autoHeight: true,
                loadData: function(data) {
                    Ext.each(this.items.items, function(item, index, allitems) {
                        item.loadData(data);
                    });
                }
            });
            NotificationTabPanel.superclass.constructor.apply(this, arguments);
        }
    });

    var triggersComboStore = new Ext.data.DirectStore({
        fields:['uuid','name'],
        directFn: router.getTriggers,
        root: 'data',
        autoLoad: true
    });

    displayNotificationEditDialogue = function(data) {
        var tab_notification, tab_content, tab_subscriptions;
        var _width, _height;

        // This action map is used to make the 'type' display in the
        // recipients grid more user friendly.
        var ACTION_TYPE_MAP = {
            'email': _t('Email'),
            'page': _t('Page'),
            'command': _t('Command'),
            'trap': _t('SNMP Trap')
        };

        if (data.action == 'email') {
            tab_content = new NotificationTabContent({
                title: 'Content',
                items: [
                    new Ext.form.ComboBox({
                        id: 'htmltextcombo',
                        store: new Ext.data.ArrayStore({
                            autoDestroy: true,
                            id: 0,
                            fields:['value','label'],
                            data: [
                                ['html','HTML'],
                                ['text','Text']
                            ]
                        }),
                        name: 'body_content_type',
                        ref: 'body_content_type',
                        allowBlank:false,
                        required:true,
                        editable:false,
                        displayField:'label',
                        valueField:'value',
                        fieldLabel: _t('Body Content Type'),
                        mode:'local',
                        triggerAction: 'all'
                    }),{
                        xtype: 'textfield',
                        name: 'subject_format',
                        ref: 'subject_format',
                        fieldLabel: _t('Message (Subject) Format')
                    },{
                        xtype: 'textarea',
                        name: 'body_format',
                        ref: 'body_format',
                        fieldLabel: _t('Body Format')
                    },{
                        xtype: 'textfield',
                        name: 'clear_subject_format',
                        ref: 'clear_subject_format',
                        fieldLabel: _t('Clear Message (Subject) Format')
                    },{
                        xtype: 'textarea',
                        name: 'clear_body_format',
                        ref: 'clear_body_format',
                        fieldLabel: _t('Clear Body Format')
                    }

                ],
                loadData: function(data) {
                    this.body_content_type.setValue(data.body_content_type);
                    this.subject_format.setValue(data.subject_format);
                    this.body_format.setValue(data.body_format);
                    this.clear_subject_format.setValue(data.clear_subject_format);
                    this.clear_body_format.setValue(data.clear_body_format);
                }
            });
        }
        else if (data.action == 'command') {
            tab_content = new NotificationTabContent({
                title: 'Content',
                items: [{
                    xtype: 'numberfield',
                    allowNegative: false,
                    allowBlank: false,
                    name: 'action_timeout',
                    ref: 'action_timeout',
                    fieldLabel: _t('Command Timeout')
                },{
                    xtype: 'textarea',
                    name: 'body_format',
                    ref: 'body_format',
                    fieldLabel: _t('Shell Command')
                },{
                    xtype: 'textarea',
                    name: 'clear_body_format',
                    ref: 'clear_body_format',
                    fieldLabel: _t('Clear Shell Command')
                }],
                loadData: function(data) {
                    this.body_format.setValue(data.body_format);
                    this.clear_body_format.setValue(data.clear_body_format);
                    this.action_timeout.setValue(data.action_timeout);
                }
            });
        }
        else if (data.action == 'trap') {
            tab_content = new NotificationTabContent({
                title: 'Content',
                items: [{
                    xtype: 'textfield',
                    name: 'action_destination',
                    ref: 'action_destination',
                    fieldLabel: _t('SNMP Trap Destination')
                }],
                loadData: function(data) {
                    this.action_destination.setValue(data.action_destination);
                }
            });
        }
        else {
            tab_content = new NotificationTabContent({
                title: 'Content',
                items: [{
                    xtype: 'textfield',
                    name: 'subject_format',
                    ref: 'subject_format',
                    fieldLabel: _t('Message (Subject) Format')
                }],
                loadData: function(data) {
                    this.subject_format.setValue(data.subject_format);
                }
            });
        }


        if (!data['userWrite']) {
            disableTabContents(tab_content);
        }

        /**
         * This awesome function from Ian fixes dumb ext combo boxes.
         */
        var smarterSetValue = function(val) {
            if (!this.loaded) {
                this.store.load({
                    callback: function(){
                        this.loaded = true;
                        Ext.form.ComboBox.prototype.setValue.call(this, val);
                        if (this.typeAhead) {
                            this.taTask.cancel();
                        }
                        this.collapse();
                    },
                    scope: this
                });
            } else {
                Ext.form.ComboBox.prototype.setValue.call(this, val);
            }
        };

        var triggersComboBox = new Ext.form.ComboBox({
            store: triggersComboStore,
            setValue: smarterSetValue,
            mode: 'local',
            lazyRender: false,
            ref: 'subscriptions',
            name: 'subscriptions',
            allowBlank:false,
            required:true,
            editable:false,
            displayField:'name',
            valueField:'uuid',
            triggerAction: 'all',
            fieldLabel: _t('Trigger'),
            typeAhead: true
        });


        tab_notification = new NotificationTabContent({
            title: 'Notification',
            items: [
                {
                    xtype: 'hidden',
                    name: 'uid',
                    ref: 'uid'
                },{
                    xtype: 'checkbox',
                    name: 'enabled',
                    ref: 'enabled',
                    fieldLabel: _t('Enabled')
                },{
                    xtype: 'checkbox',
                    name: 'send_clear',
                    ref: 'send_clear',
                    fieldLabel: _t('Send Clear')
                },{
                    xtype: 'checkbox',
                    name: 'send_initial_occurrence',
                    ref: 'send_initial_occurrence',
                    fieldLabel: _t('Send only on Initial Occurence?')
                },{
                    xtype: 'numberfield',
                    name: 'delay_seconds',
                    allowNegative: false,
                    allowBlank: false,
                    ref: 'delay_seconds',
                    fieldLabel: _t('Delay (seconds)')
                },{
                    xtype: 'numberfield',
                    allowNegative: false,
                    allowBlank: false,
                    name: 'repeat_seconds',
                    ref: 'repeat_seconds',
                    fieldLabel: _t('Repeat (seconds)')
                },
                triggersComboBox
            ],
            loadData: function(data) {
                this.uid.setValue(data.uid);
                this.enabled.setValue(data.enabled);
                this.delay_seconds.setValue(data.delay_seconds);
                this.send_clear.setValue(data.send_clear);
                this.repeat_seconds.setValue(data.repeat_seconds);
                this.subscriptions.setValue(data.subscriptions);
                this.send_initial_occurrence.setValue(data.send_initial_occurrence);
            }
        });

        if (!data['userWrite']) {
            disableTabContents(tab_notification);
        }

        var recipients_grid = new UsersPermissionGrid({
            title: _t('Subscribers'),
            allowManualEntry: true,
            ref: 'recipients_grid'
        });

        var tab_recipients = new NotificationTabContent({
            title: 'Subscribers',
            ref: 'recipients_tab',
            layout: {
                type: 'vbox',
                align: 'stretch'
            },
            items: [{
                xtype: 'panel',
                unstyled: true,
                border: false,
                layout: 'form',
                autoScroll: true,
                title: _t('Global Options'),
                items: [
                    {
                        xtype:'checkbox',
                        name: 'notification_globalRead',
                        ref: '../globalRead',
                        boxLabel: _t('Everyone can view'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'notification_globalWrite',
                        ref: '../globalWrite',
                        boxLabel: _t('Everyone can edit content'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'notification_globalManage',
                        ref: '../globalManage',
                        boxLabel: _t('Everyone can manage subscriptions'),
                        hideLabel: true
                    }
                ]
            },
            recipients_grid
            ],
            loadData: function(data) {
                this.recipients_grid.getStore().loadData(data.recipients);
                this.globalRead.setValue(data.globalRead);
                this.globalWrite.setValue(data.globalWrite);
                this.globalManage.setValue(data.globalManage);
            }
        });

        if (!data['userManage']) {
            disableTabContents(tab_recipients);
        }

        var tab_panel = new NotificationTabPanel({
            items: [
                // NOTIFICATION INFO
                tab_notification,

                // CONTENT TAB
                tab_content,

                // RECIPIENTS
                tab_recipients
            ]
        });

        var dialogue = new EditNotificationDialogue({
            id: 'edit_notification_dialogue',
            title: _t('Edit Notification Subscription'),
            directFn: router.updateNotification,
            reloadFn: reloadNotificationGrid,
            tabPanel: tab_panel
        });

        dialogue.loadData(data);
        dialogue.show();
    };

    var displayNotificationAddDialogue = function() {
        var dialogue = new Ext.Window({
            title: 'Add Notification',
            height: 140,
            width: 300,
            modal: true,
            plain: true,
            items: [{
                xtype:'form',
                ref: '../addForm',
                border: false,
                monitorValid: true,
                buttonAlign: 'center',
                items:[
                    {
                        xtype: 'textfield',
                        name: 'newId',
                        ref: '../newId',
                        allowBlank: false,
                        vtype: 'alphanum',
                        fieldLabel: _t('Id')
                    }, new Ext.form.ComboBox({
                        store: new Ext.data.ArrayStore({
                            autoDestroy: true,
                            fields:['value','label'],
                            id: 0,
                            data: [
                                ['email','Email'],
                                ['page','Page'],
                                ['command','Command'],
                                ['trap', 'SNMP Trap']
                            ]
                        }),
                        name:'action',
                        ref: 'action_combo',
                        allowBlank:false,
                        required:true,
                        editable:false,
                        displayField:'label',
                        valueField:'value',
                        fieldLabel: _t('Action'),
                        mode:'local',
                        triggerAction: 'all'
                    })
                ],
                buttons:[
                    {
                        xtype: 'button',
                        ref: 'submitButton',
                        formBind: true,
                        text: _t('Submit'),
                        handler: function(button) {
                            var params = button.refOwner.ownerCt.getForm().getFieldValues();
                            router.addNotification(params, function(){
                                reloadNotificationGrid();
                                button.refOwner.ownerCt.ownerCt.close();
                            });
                        }
                    },{
                        xtype: 'button',
                        ref: 'cancelButton',
                        text: _t('Cancel'),
                        handler: function(button) {
                            button.refOwner.ownerCt.ownerCt.close();
                        }
                    }
                ]
            }]
        });
        dialogue.show();
    };

    EditNotificationDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                autoScroll: true,
                border: false,
                width: 500,
                height: 380,
                layout: 'fit',
                items: [{
                    xtype:'form',
                    autoHeight: true,
                    ref: 'editForm',
                    border: false,
                    buttonAlign: 'center',
                    monitorValid: true,
                    items:[config.tabPanel],
                    buttons:[{
                        xtype: 'button',
                        text: _t('Submit'),
                        ref: '../../submitButton',
                        formBind: true,
                        handler: function(button) {
                            var params = button.refOwner.editForm.getForm().getFieldValues();
                            params.recipients = [];
                            Ext.each(
                                button.refOwner.tabPanel.recipients_tab.recipients_grid.getStore().getRange(),
                                function(item, index, allItems){
                                    params.recipients.push(item.data);
                                }
                            );
                            config.directFn(params, function(){
                                button.refOwner.close();
                                config.reloadFn();
                            });
                        }
                    },{
                        xtype: 'button',
                        ref: '../../cancelButton',
                        text: _t('Cancel'),
                        handler: function(button) {
                            button.refOwner.close();
                        }
                    }]
                }]
            });
            EditNotificationDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            this.tabPanel.loadData(data);
        }
    });
    Ext.reg('editnotificationdialogue', EditNotificationDialogue);


    EditScheduleDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                width: 450,
                border: false,
                closeAction: 'hide',
                items:{
                    xtype:'form',
                    ref: 'editForm',
                    border: false,
                    buttonAlign: 'center',
                    monitorValid: true,
                    autoWidth: true,
                    items:[
                        {
                            xtype: 'hidden',
                            name: 'uid',
                            ref: 'uid'
                        },{
                            xtype: 'checkbox',
                            name: 'enabled',
                            ref: 'enabled',
                            fieldLabel: _t('Enabled')
                        },{
                            xtype: 'datefield',
                            name: 'start',
                            ref: 'start',
                            allowBlank: false,
                            fieldLabel: _t('Start Date')
                        }, {
                            xtype: 'timefield',
                            name: 'starttime',
                            ref: 'starttime',
                            allowBlank: false,
                            format: 'H:i',
                            fieldLabel: _t('Start Time')
                        },
                        new Ext.form.ComboBox({
                            store: new Ext.data.ArrayStore({
                                autoDestroy: true,
                                fields:['value'],
                                id: 0,
                                data: [
                                    ['Never'],
                                    ['Daily'],
                                    ['Every Weekday'],
                                    ['Weekly'],
                                    ['Monthly'],
                                    ['First Sunday of the Month']
                                ]
                            }),
                            mode: 'local',
                            name: 'repeat',
                            allowBlank: false,
                            required: true,
                            editable: false,
                            displayField: 'value',
                            valueField: 'value',
                            triggerAction: 'all',
                            fieldLabel: _t('Repeat')
                        }),{
                            xtype: 'textfield',
                            name: 'duration',
                            ref: 'duration',
                            fieldLabel: _t('Duration')
                        }
                    ],
                    buttons:[
                        {
                            xtype: 'button',
                            text: _t('Submit'),
                            ref: '../../submitButton',
                            formBind: true,
                            handler: function(button) {
                                var params = button.refOwner.editForm.getForm().getFieldValues();
                                config.directFn(params, function(){
                                    button.refOwner.hide();
                                    config.reloadFn();
                                });
                            }
                        },{
                            xtype: 'button',
                            ref: '../../cancelButton',
                            text: _t('Cancel'),
                            handler: function(button) {
                                button.refOwner.hide();
                            }
                        }]
                    }
            });
            EditScheduleDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            Ext.each(this.editForm.items.items, function(item, index, allitems) {
                item.setValue(eval('data.'+item.name));
            });
        }
    });
    Ext.reg('editscheduledialogue', EditScheduleDialogue);

    editScheduleDialogue = new EditScheduleDialogue(editScheduleDialogueConfig);
    addScheduleDialogue = new AddDialogue(addScheduleDialogueConfig);


    NotificationSubscriptions = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                autoScroll: true,
                border: false,
                height: 500,
                viewConfig: {
                    forceFit: true
                },
                listeners: {
                    rowdblclick: function(grid, rowIndex, event){
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayNotificationEditDialogue(row.data);
                        }
                    }
                },
                selModel: new Ext.grid.RowSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            var row = sm.getSelected(),
                                panel = Ext.getCmp(schedulesPanelConfig.id);
                            panel.setContext(row.data.uid);
                            panel.disableButtons(false);
                            sm.grid.customizeButton.setDisabled(false);
                        },
                        rowdeselect: function(sm, rowIndex, record) {
                            Ext.getCmp(schedulesPanelConfig.id).disableButtons(true);
                            sm.grid.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                store: {
                    xtype: 'directstore',
                    directFn: router.getNotifications,
                    root: 'data',
                    autoLoad: true,
                    fields: [
                        'uid',
                        'newId',
                        'enabled',
                        'action',
                        'delay_seconds',
                        'send_clear',
                        'send_initial_occurrence',
                        'repeat_seconds',
                        'action_timeout',
                        'action_destination',
                        'body_content_type',
                        'subject_format',
                        'body_format',
                        'clear_subject_format',
                        'clear_body_format',
                        'recipients',
                        'subscriptions',
                        'globalRead',
                        'globalWrite',
                        'globalManage',
                        'userRead',
                        'userWrite',
                        'userManage'

                    ]
                },
                colModel: new Ext.grid.ColumnModel({
                    columns: [{
                        xtype: 'booleancolumn',
                        trueText: _t('Yes'),
                        falseText: _t('No'),
                        dataIndex: 'enabled',
                        header: _t('Enabled'),
                        sortable: true
                    },{
                        dataIndex: 'newId',
                        header: _t('Id'),
                        sortable: true
                    },{
                        dataIndex: 'subscriptions',
                        header: _t('Trigger'),
                        sortable: true,
                        // use a fancy renderer that get's it's display value
                        // from the store that already has the triggers.
                        renderer: function(value, metaData, record, rowIndex, colIndex, store) {
                            var idx = triggersComboStore.find('uuid', value);
                            if (idx > -1) {
                                return triggersComboStore.getAt(idx).data.name;
                            }
                            else {
                                return value;
                            }
                       }
                    },{
                        dataIndex: 'action',
                        header: _t('Action'),
                        sortable: true
                    }]
                }),
                tbar:[{
                    xtype: 'button',
                    iconCls: 'add',
                    ref: '../addButton',
                    handler: function(button) {
                        displayNotificationAddDialogue();
                    }
                },{
                    xtype: 'button',
                    iconCls: 'delete',
                    ref: '../deleteButton',
                    handler: function(button) {
                        var row = button.refOwner.getSelectionModel().getSelected(),
                            uid,
                            params,
                            callback;
                        if (row){
                            uid = row.data.uid;
                            // show a confirmation
                            Ext.Msg.show({
                                title: _t('Delete Notification Subscription'),
                                msg: String.format(_t("Are you sure you wish to delete the notification, {0}?"), row.data.newId),
                                buttons: Ext.Msg.OKCANCEL,
                                fn: function(btn) {
                                    if (btn == "ok") {
                                        params = {
                                            uid:uid
                                        };
                                        callback = function(response){
                                            var panel = Ext.getCmp(schedulesPanelConfig.id);
                                            panel.getStore().removeAll();
                                            panel.disableButtons(true);
                                            Ext.getCmp(notificationPanelConfig.id).customizeButton.setDisabled(true);
                                            reloadNotificationGrid();
                                        };
                                        router.removeNotification(params, callback);

                                    } else {
                                        Ext.Msg.hide();
                                    }
                                }
                            });
                        }
                    }
                },{
                    xtype: 'button',
                    iconCls: 'customize',
                    disabled:true,
                    ref: '../customizeButton',
                    handler: function(button){
                        var row = button.refOwner.getSelectionModel().getSelected();
                        if (row) {
                            displayNotificationEditDialogue(row.data);
                        }
                    }
                }]
            });
            NotificationSubscriptions.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid) {
            this.uid = uid;
            this.getStore().load({
                params: {
                    uid: uid
                }
            });
        }
    });
    Ext.reg('notificationsubscriptions', NotificationSubscriptions);

    notification_panel = Ext.create(notificationPanelConfig);


    SchedulesPanel = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                autoScroll: true,
                border: false,
                height: 500,
                viewConfig: {
                    forceFit: true
                },
                listeners: {
                    rowdblclick: function(grid, rowIndex, event){
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayScheduleEditDialogue(row.data);
                        }
                    }
                },
                selModel: new Ext.grid.RowSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            var row = sm.getSelected();
                            sm.grid.customizeButton.setDisabled(false);
                        },
                        rowdeselect: function(sm, rowIndex, record) {
                            sm.grid.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                store: {
                    xtype: 'directstore',
                    directFn: router.getWindows,
                    root: 'data',
                    fields: [
                        'uid',
                        'newId',
                        'enabled',
                        'start',
                        'starttime',
                        'repeat',
                        'duration'
                    ]
                },
                colModel: new Ext.grid.ColumnModel({
                    columns: [{
                        dataIndex: 'enabled',
                        header: _t('Enabled'),
                        sortable: true
                    },{
                        dataIndex: 'newId',
                        header: _t('Id'),
                        width:200,
                        sortable: true
                    },{
                        dataIndex: 'start',
                        header: _t('Start'),
                        width:200,
                        sortable: true
                    }]
                }),
                tbar:[{
                    xtype: 'button',
                    iconCls: 'add',
                    ref: '../addButton',
                    disabled: true,
                    handler: function(button) {
                        addScheduleDialogue.show();
                    }
                },{
                    xtype: 'button',
                    iconCls: 'delete',
                    ref: '../deleteButton',
                    disabled: true,
                    handler: function(button) {
                        var row = button.refOwner.getSelectionModel().getSelected(),
                            uid,
                            params;
                        if (row){
                            uid = row.data.uid;
                            // show a confirmation
                            Ext.Msg.show({
                                title: _t('Delete Subscription Schedule'),
                                msg: String.format(_t("Are you sure you wish to delete the schedule, {0}?"), row.data.newId),
                                buttons: Ext.Msg.OKCANCEL,
                                fn: function(btn) {
                                    if (btn == "ok") {
                                        params = {
                                            uid:uid
                                        };
                                        router.removeWindow(params, reloadScheduleGrid);
                                    } else {
                                        Ext.Msg.hide();
                                    }
                                }
                            });
                        }
                    }
                },{
                    xtype: 'button',
                    iconCls: 'customize',
                    disabled:true,
                    ref: '../customizeButton',
                    handler: function(button){
                        var row = button.refOwner.getSelectionModel().getSelected();
                        if (row) {
                            displayScheduleEditDialogue(row.data);
                        }
                    }
                }]

            });
            SchedulesPanel.superclass.constructor.apply(this, arguments);
        },
        setContext: function(uid){
            this.uid = uid;
            this.getStore().load({
                params: {
                    uid: uid
                }
            });
            this.disableButtons(false);
            this.customizeButton.setDisabled(true);
        },
        disableButtons: function(bool){
            this.addButton.setDisabled(bool);
            this.deleteButton.setDisabled(bool);
        }
    });
    Ext.reg('schedulespanel', SchedulesPanel);

    schedules_panel = Ext.create(schedulesPanelConfig);


    NotificationPageLayout = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                id: 'notification_subscription_panel',
                layout:'border',
                defaults: {
                    collapsible: false,
                    split: true,
                    border: false
                },
                items: [{
                    title: _t('Notification Subscription Schedules'),
                    region:'east',
                    width: 375,
                    minSize: 100,
                    maxSize: 375,
                    items: [config.schedulePanel]
                },{
                    title: _t('Notification Subscriptions'),
                    region:'center',
                    items:[config.notificationPanel]
                }]

            });
            NotificationPageLayout.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('notificationsubscriptions', NotificationPageLayout);


    notificationsPanelConfig = {
        id: 'notifications_panel',
        xtype: 'notificationsubscriptions',
        schedulePanel: schedules_panel,
        notificationPanel: notification_panel
    };




    /***
     * TRIGGERS
     **/

    colModelConfig = {
        defaults: {
            menuDisabled: true
        },
        columns: [
            {
                id: 'enabled',
                dataIndex: 'enabled',
                header: _t('Enabled'),
                xtype: 'booleancolumn',
                width: 70,
                sortable: true
            }, {
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                width: 200,
                sortable: true
            }
        ]
    };

    triggersPanelConfig = {
        id: 'triggers_grid_panel',
        xtype: 'TriggersGridPanel'
    };

    detailPanelConfig = {
        id: 'triggers_detail_panel',
        xtype: 'contextcardpanel',
        split: true,
        region: 'center',
        layout: 'card',
        activeItem: 0,
        items: [triggersPanelConfig, notificationsPanelConfig]
    };

    navSelectionModel = new Ext.tree.DefaultSelectionModel({
        listeners: {
            selectionchange: function (sm, newnode) {
                var p = Ext.getCmp(detailPanelConfig.id);
                p.layout.setActiveItem(newnode.attributes.target);
                p.setContext(newnode.attributes.target);
            }
        }
    });

    masterPanelConfig = {
        id: 'master_panel',
        region: 'west',
        split: 'true',
        width: 275,
        autoScroll: false,
        items: [
            {
                id: 'master_panel_navigation',
                xtype: 'treepanel',
                region: 'west',
                split: 'true',
                width: 275,
                autoScroll: true,
                border: false,
                rootVisible: false,
                selModel: navSelectionModel,
                layout: 'fit',
                bodyStyle: { 'margin-top' : 10 },
                root: {
                    text: 'Trigger Navigation',
                    draggable: false,
                    id: 'trigger_root',
                    expanded: true,
                    children: [
                        {
                            target: triggersPanelConfig.id,
                            text: 'Triggers',
                            leaf: true,
                            iconCls: 'no-icon'
                        }, {
                            target: notificationsPanelConfig.id,
                            text: 'Notifications',
                            leaf: true,
                            iconCls: 'no-icon'
                        }
                    ]
                }
            }
        ]
    };

    var trigger_tab_content = {
        xtype:'panel',
        ref: '../../tab_content',
        height: 370,
        autoScroll: true,
        layout: 'form',
        title: 'Trigger',
        items:[
            {
                xtype: 'hidden',
                name: 'uuid',
                ref: 'uuid'
            },{
                xtype: 'textfield',
                name: 'name',
                ref: 'name',
                allowBlank: false,
                fieldLabel: _t('Name')
            },{
                xtype: 'checkbox',
                name: 'enabled',
                ref: 'enabled',
                fieldLabel: _t('Enabled')
            },{
                xtype: 'rulebuilder',
                fieldLabel: _t('Rule'),
                name: 'criteria',
                id: 'rulebuilder',
                ref: 'rule',
                subjects: [{
                    text: _t('Device Priority'),
                    value: 'dev.priority',
                    comparisons: NUMCMPS
                },{
                    text: _t('Device Production State'),
                    value: 'dev.production_state',
                    comparisons: NUMCMPS
                },{
                    text: _t('Device (Element)'),
                    value: 'elem.name',
                    comparisons: STRINGCMPS
                },{
                    text: _t('Component (Sub-Element)'),
                    value: 'sub_elem.name',
                    comparisons: STRINGCMPS
                },{
                    text: _t('Element Type'),
                    value: 'elem.type',
                    comparisons: ZFR.IDENTITYCOMPARISONS,
                    field: {
                        xtype: 'combo',
                        mode: 'local',
                        valueField: 'name',
                        displayField: 'name',
                        typeAhead: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        store: new Ext.data.ArrayStore({
                            fields: ['name'],
                            data: [[
                                'COMPONENT'
                            ],[
                                'DEVICE'
                            ],[
                                'SERVICE'
                            ],[
                                'ORGANIZER'
                            ]]
                        })
                    }
                },{
                    text: _t('Sub Element Type'),
                    value: 'sub_elem.type',
                    comparisons: ZFR.IDENTITYCOMPARISONS,
                    field: {
                        xtype: 'combo',
                        mode: 'local',
                        valueField: 'name',
                        displayField: 'name',
                        typeAhead: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        store: new Ext.data.ArrayStore({
                            fields: ['name'],
                            data: [[
                                'COMPONENT'
                            ],[
                                'DEVICE'
                            ],[
                                'SERVICE'
                            ],[
                                'ORGANIZER'
                            ]]
                        })
                    }
                }, {
                    text: _t('Event Class'),
                    value: 'evt.event_class',
                    comparisons: STRINGCMPS,
                    field: {
                        xtype: 'eventclass'
                    }
                },{
                    text: _t('Event Key'),
                    value: 'evt.event_key',
                    comparisons: STRINGCMPS
                },{
                    text: _t('Summary'),
                    value: 'evt.summary',
                    comparisons: STRINGCMPS
                },{
                    text: _t('Message'),
                    value: 'evt.message',
                    comparisons: STRINGCMPS
                },
                    ZFR.EVENTSEVERITY,
                {
                    text: _t('Fingerprint'),
                    value: 'evt.fingerprint',
                    comparisons: STRINGCMPS
                },{
                    text: _t('Agent'),
                    value: 'evt.agent',
                    comparisons: STRINGCMPS
                },{
                    text: _t('Monitor'),
                    value: 'evt.monitor',
                    comparisons: STRINGCMPS
                },{
                    text: _t('Count'),
                    value: 'evt.count',
                    comparisons: NUMCMPS,
                    field: {
                        xtype: 'numberfield'
                    }
                },{
                    text: _t('Status'),
                    value: 'evt.status',
                    comparisons: NUMCMPS,
                    field: {
                        xtype: 'combo',
                        mode: 'local',
                        valueField: 'value',
                        displayField: 'name',
                        typeAhead: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        store: new Ext.data.ArrayStore({
                            fields: ['name', 'value'],
                            data: [[
                                _t('New'), 1
                            ],[
                                _t('Acknowledged'), 2
                            ],[
                                _t('Suppressed'), 3
                            ],[
                                _t('Closed'), 4
                            ],[
                                _t('Cleared'), 5
                            ],[
                                _t('Dropped'), 6
                            ],[
                                _t('Aged'), 7
                            ]]
                        })
                    }
                }]
            }
        ]
    };
    
    var users_grid = new UsersPermissionGrid({
        title: _t('Users'),
        allowManualEntry: false
    });

    var trigger_tab_users = {
        xtype: 'panel',
        ref: '../../tab_users',
        title: 'Users',
        autoScroll: true,
        height: 350,
        items: [
            {
                xtype: 'panel',
                unstyled: true,
                border: false,
                layout: 'form',
                title: _t('Global Options'),
                items: [
                    {
                        xtype:'checkbox',
                        name: 'trigger_globalRead',
                        ref: '../globalRead',
                        boxLabel: _t('Everyone can view'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'trigger_globalWrite',
                        ref: '../globalWrite',
                        boxLabel: _t('Everyone can edit content'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'trigger_globalManage',
                        ref: '../globalManage',
                        boxLabel: _t('Everyone can manage users'),
                        hideLabel: true
                    }

                ]
            },
            users_grid
        ]
    };


    EditTriggerDialogue = Ext.extend(Ext.Window, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                height: 500,
                width: 840,
                boxMaxWidth: 840, // for chrome, safari
                border: false,
                closeAction: 'hide',
                layout: 'fit',
                items: [
                    {
                        xtype:'form',
                        ref: 'wrapping_form',
                        border: false,
                        buttonAlign: 'center',
                        monitorValid: true,
                        items: [
                            {
                                xtype: 'tabpanel',
                                ref: '../tabs',
                                activeTab: 0,
                                activeIndex: 0,
                                unstyled: true,
                                defaults: {
                                    unstyled: true,
                                    padding: 10,
                                    frame: false,
                                    border: false
                                },
                                items: [
                                    trigger_tab_content,
                                    trigger_tab_users
                                ]
                            }
                        ],
                        buttons:[
                            {
                                xtype: 'button',
                                text: _t('Submit'),
                                ref: '../../submitButton',
                                formBind: true,
                                handler: function(button) {
                                    var tab_content = button.refOwner.tab_content,
                                        tab_users = button.refOwner.tab_users;

                                    var params = {
                                        uuid: tab_content.uuid.getValue(),
                                        enabled: tab_content.enabled.getValue(),
                                        name: tab_content.name.getValue(),
                                        rule: {
                                            source: tab_content.rule.getValue()
                                        },

                                        // tab_users
                                        globalRead: tab_users.globalRead.getValue(),
                                        globalWrite: tab_users.globalWrite.getValue(),
                                        globalManage: tab_users.globalManage.getValue(),

                                        /*

                                        var params = button.refOwner.editForm.getForm().getFieldValues();
                            params.recipients = [];
                            Ext.each(
                                button.refOwner.tabPanel.recipients_tab.recipients_grid.getStore().getRange(),
                                function(item, index, allItems){
                                    params.recipients.push(item.data);
                                }
                            );
                            config.directFn(params, function(){
                                button.refOwner.close();
                                config.reloadFn();
                            });


                                         */
                                        users: []
                                    };

                                    Ext.each(
                                        tab_users.users_grid.getStore().getRange(),
                                        function(item, index, allItems){
                                            params.users.push(item.data);
                                        }
                                    );

                                    config.directFn(params, function(){
                                        reloadTriggersGrid();
                                        button.refOwner.hide();
                                    });
                                }
                            },{
                                xtype: 'button',
                                ref: '../../cancelButton',
                                text: _t('Cancel'),
                                handler: function(button) {
                                    button.refOwner.hide();
                                }
                            }
                        ]
                    }
                ]
            });
            EditTriggerDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            // set content stuff.
            this.tab_content.uuid.setValue(data.uuid);
            this.tab_content.enabled.setValue(data.enabled);
            this.tab_content.name.setValue(data.name);
            this.tab_content.rule.setValue(data.rule.source);

            // set users information (permissions and such)
            this.tab_users.globalRead.setValue(data.globalRead);
            this.tab_users.globalWrite.setValue(data.globalWrite);
            this.tab_users.globalManage.setValue(data.globalManage);
            
            this.tab_users.users_grid.getStore().loadData(data.users);
            
        }
    });
    Ext.reg('edittriggerdialogue', EditTriggerDialogue);


    reloadTriggersGrid = function() {
        Ext.getCmp(triggersPanelConfig.id).getStore().reload();
    };

    displayEditTriggerDialogue = function(data) {
        editTriggerDialogue.loadData(data);
        
        if (!data['userWrite']) {
            disableTabContents(editTriggerDialogue.tab_content);
        } else {
            enableTabContents(editTriggerDialogue.tab_content);
        }

        if (!data['userManage']) {
            disableTabContents(editTriggerDialogue.tab_users);
        } else {
            enableTabContents(editTriggerDialogue.tab_users);
        }
        
        editTriggerDialogue.show();
    };

    addTriggerDialogue = new AddDialogue({
        title: _t('Add Trigger'),
        directFn: router.addTrigger,
        reloadFn: reloadTriggersGrid
    });

    editTriggerDialogue = new EditTriggerDialogue({
        title: _t('Edit Trigger'),
        directFn: router.updateTrigger,
        reloadFn: reloadTriggersGrid,
        validateFn: router.parseFilter
    });

    colModel = new Ext.grid.ColumnModel(colModelConfig);

    TriggersGridPanel = Ext.extend(Ext.grid.GridPanel, {
        constructor: function(config) {
            Ext.applyIf(config, {
                autoExpandColumn: 'name',
                stripeRows: true,
                cm: colModel,
                title: _t('Triggers'),
                store: {
                    xtype: 'directstore',
                    directFn: router.getTriggers,
                    root: 'data',
                    autoLoad: true,
                    fields: ['uuid', 'enabled', 'name', 'rule', 'users',
                        'globalRead', 'globalWrite', 'globalManage',
                        'userRead', 'userWrite', 'userManage']
                },
                sm: new Ext.grid.RowSelectionModel({
                    singleSelect: true,
                    listeners: {
                        rowselect: function(sm, rowIndex, record) {
                            // enable/disabled the edit button
                            sm.grid.deleteButton.setDisabled(false);
                            sm.grid.customizeButton.setDisabled(false);
                        },
                        rowdeselect: function(sm, rowIndex, record) {
                            sm.grid.deleteButton.setDisabled(true);
                            sm.grid.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                listeners: {
                    rowdblclick: function(grid, rowIndex, event) {
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayEditTriggerDialogue(row.data);
                        }
                    }
                },
                tbar:[
                    {
                        xtype: 'button',
                        iconCls: 'add',
                        ref: '../addButton',
                        handler: function(button) {
                            addTriggerDialogue.show();
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        ref: '../deleteButton',
                        handler: function(button) {
                            var row = button.refOwner.getSelectionModel().getSelected(),
                                uuid, params, callback;
                            if (row){
                                uuid = row.data.uuid;
                                // show a confirmation
                                Ext.Msg.show({
                                    title: _t('Delete Trigger'),
                                    msg: String.format(_t("Are you sure you wish to delete the trigger, {0}?"), row.data.name),
                                    buttons: Ext.Msg.OKCANCEL,
                                    fn: function(btn) {
                                        if (btn == "ok") {
                                            params= {
                                                uuid:uuid
                                            };
                                            callback = function(response){
                                                // item removed, reload grid.
                                                button.refOwner.deleteButton.setDisabled(true);
                                                button.refOwner.customizeButton.setDisabled(true);
                                                reloadTriggersGrid();
                                            };
                                            router.removeTrigger(params, callback);

                                        } else {
                                            Ext.Msg.hide();
                                        }
                                    }
                                });
                            }
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'customize',
                        disabled:true,
                        ref: '../customizeButton',
                        handler: function(button){
                            var row = button.refOwner.getSelectionModel().getSelected();
                            if (row) {
                                displayEditTriggerDialogue(row.data);
                            }
                        }
                    }
                ]
            });
            TriggersGridPanel.superclass.constructor.call(this, config);
        },
        setContext: function(uid) {
            // triggers are not context aware.
            this.getStore().load();
        }
    });
    Ext.reg('TriggersGridPanel', TriggersGridPanel);

    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        defaults: {
            'border':false
        },
        items: [
            masterPanelConfig,  // navigation
            detailPanelConfig   // content panel
        ]
    });

});