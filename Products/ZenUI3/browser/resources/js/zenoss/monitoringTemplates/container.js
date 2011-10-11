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

Ext.ns('Zenoss', 'Zenoss.templates');

var REMOTE = Zenoss.remote.DeviceRouter;

/**
 * Updates the data store for the template tree. This will select the
 * first template when refreshed.
 **/
function refreshTemplateTree() {
    var cmp = Ext.getCmp('templateTree');
    if (cmp && cmp.isVisible()) {

        cmp.refresh(function() {
            // select the first node
            var root = cmp.getRootNode();
            if (root.firstChild) {
                root.firstChild.select();
            }
        });

    }
}

Ext.define("Zenoss.templates.Container", {
    alias:['widget.templatecontainer'],
    extend:"Ext.Panel",
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'border',
            border: false,
            defaults: {
                border: false,
                split: true
            },
            items: [{
                xtype: 'DataSourceTreeGrid',
                id: 'dataSourceTreeGrid',
                region: 'center',
                ref: 'dataSourceTreeGrid',
                root: {
                    uid: config.uid,
                    id: config.uid
                }
            }, {
                xtype: 'panel',
                layout: 'border',
                region: 'east',
                width: '35%',
                defaults: {
                    border: false,
                    split: true
                },
                items: [{
                    xtype: 'thresholddatagrid',
                    id: 'thresholdGrid',
                    ref: '../thresholdGrid',
                    region: 'north',
                    height: 300
                }, {
                    xtype: 'graphgrid',
                    id: 'graphGrid',
                    ref: '../graphGrid',
                    region: 'center'
                }]
            }]
        });
        Zenoss.templates.Container.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        this.updateTreeGrid(this.dataSourceTreeGrid, uid);
        this.updateGrid(this.thresholdGrid, uid);
        this.updateGrid(this.graphGrid, uid);
    },
    updateTreeGrid: function(treeGrid, uid){
        treeGrid.setContext(uid);
    },
    updateGrid: function(grid, uid) {
        grid.setContext(uid);
    }
});


Zenoss.BubblingSelectionModel = Ext.extend(Zenoss.TreeSelectionModel, {
    constructor: function(config) {
        Zenoss.BubblingSelectionModel.superclass.constructor.call(this, config);
        this.enableBubble('selectionchange');
        this.bubbleTarget = config.bubbleTarget;
    },
    getBubbleTarget: function() {
        return this.bubbleTarget;
    }
});

Zenoss.MonTemplateSelectionModel = Ext.extend(Zenoss.BubblingSelectionModel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            listeners: {
                beforeselect: function(sm, node) {
                    return node.isLeaf();
                }
            }
        });
        Zenoss.MonTemplateSelectionModel.superclass.constructor.call(this, config);
    }
});

Ext.define("Zenoss.templates.MonTemplateTreePanel", {
    alias:['widget.montemplatetreepanel'],
    extend:"Ext.tree.TreePanel",
    constructor: function(config){
        // create the model
        Ext.applyIf(config, {
            useArrows: true,
            border: false,
            cls: 'x-tree-noicon',
            selModel: new Zenoss.MonTemplateSelectionModel({
                bubbleTarget: config.bubbleTarget
            }),
            root: {
                text: _t('Monitoring Templates')
            }
        });
        Zenoss.templates.MonTemplateTreePanel.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        if ( uid.match('^/zport/dmd/Devices') ) {
            REMOTE.getTemplates({id: uid}, function(response){
                var root = {
                    expanded: true,
                    text: _t('Monitoring Templates'),
                    children: response
                };

                this.setRootNode(root);
                // resize ourself with the new data
                this.doLayout();
            } , this);
        } else {
            this.hide();
        }
    },
    onSelectionChange: function(nodes) {
        var detail, node, uid;
        if (nodes && nodes.length) {
            node = nodes[0];
            uid = node.get("id");
            detail = Ext.getCmp(this.initialConfig.detailPanelId);
            if ( ! detail.items.containsKey('montemplate') ) {
                detail.add({
                    xtype: 'templatecontainer',
                    id: 'montemplate',
                    ref: 'montemplate',
                    uid: uid
                });
            }
            detail.montemplate.setContext(uid);
            detail.getLayout().setActiveItem('montemplate');
        }
    }
});


Ext.define("Zenoss.BindTemplatesItemSelector", {
    alias:['widget.bindtemplatesitemselector'],
    extend:"Ext.ux.form.ItemSelector",
        constructor: function(config) {
        Ext.applyIf(config, {
            imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
            drawUpIcon: false,
            drawDownIcon: false,
            drawTopIcon: false,
            drawBotIcon: false,
            displayField: 'name',
            valueField: 'id',
            store:  Ext.create('Ext.data.ArrayStore', {
                data: [],
                fields: ['id','name'],
                sortInfo: {
                    field: 'value',
                    direction: 'ASC'
                }
            })
        });
        Zenoss.BindTemplatesItemSelector.superclass.constructor.apply(this, arguments);
    },
    setContext: function(uid) {
        REMOTE.getUnboundTemplates({uid: uid}, function(provider, response){
            var data = response.result.data;
            // stack the calls so we can make sure the store is setup correctly first
            REMOTE.getBoundTemplates({uid: uid}, function(provider, response){
                var results = [];
                Ext.each(response.result.data, function(row){
                    results.push(row[0]);
                    data.push(row);
                });
                this.store.loadData(data);
                this.bindStore(this.store);
                this.setValue(results);
            }, this);
        }, this);

    }
});


Ext.define("Zenoss.AddLocalTemplatesDialog", {
    alias:['widget.addlocaltemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            title: _t('Add Local Template'),
            layout: 'anchor',
            items: [{
                xtype: 'form',
                ref: 'formPanel',
                border: false,
                monitorValid: true,
                listeners: {
                    clientvalidation: function(formPanel, valid) {
                        var dialogWindow = formPanel.refOwner;
                        dialogWindow.submitButton.setDisabled( ! valid );
                    }
                },
                items: [{
                    xtype: 'idfield',
                    fieldLabel: _t('Name'),
                    ref: 'templateName',
                    context: config.context
                }]
            }],
            listeners: {
                show: function() {
                    this.formPanel.templateName.setValue('');
                }

            },
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                ref: '../submitButton',
                text: _t('Submit'),
                handler: function() {
                    var templateId = me.formPanel.templateName.getValue();

                    REMOTE.addLocalTemplate({
                       deviceUid: me.context,
                       templateId: templateId
                    }, refreshTemplateTree);
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                text: _t('Cancel')
            }]
        });
        Zenoss.AddLocalTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


Ext.define("Zenoss.BindTemplatesDialog", {
    alias:['widget.bindtemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        var itemId = Ext.id();

        Ext.applyIf(config, {
            title: _t('Bind Templates'),
            items: {
                xtype: 'bindtemplatesitemselector',
                ref: 'itemselector',
                id: itemId,
                context: config.context
            },
            listeners: {
                show: function() {
                    Ext.getCmp(itemId).setContext(this.context);
                }
            },
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                text: _t('Save'),
                handler: function(){
                    var records, data, templateIds;
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        templateIds = Ext.getCmp(itemId).getValue();
                        REMOTE.setBoundTemplates({
                            uid: me.context,
                            templateIds: templateIds
                        }, refreshTemplateTree);
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                text: _t('Cancel')
            }]
        });
        Zenoss.BindTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


Ext.define("Zenoss.ResetTemplatesDialog", {
    alias:['widget.resettemplatesdialog'],
    extend:"Zenoss.MessageDialog",
    constructor: function(config) {
        var me = this;
        Ext.applyIf(config, {
            title: _t('Reset Template Bindings'),
            message: _t('Are you sure you want to delete all local template bindings and use default values?'),
            buttons: [
                {
                    xtype: 'HideDialogButton',
                    ui: 'dialog-dark',                    
                    text: _t('Reset Bindings'),
                    handler: function() {
                        if (Zenoss.Security.hasPermission('Manage DMD')) {
                            REMOTE.resetBoundTemplates(
                                { uid: me.context },
                                refreshTemplateTree);
                        }
                    }
                }, {
                    xtype: 'HideDialogButton',
                    ui: 'dialog-dark',                    
                    text: _t('Cancel')
                }
            ]
        });
        Zenoss.ResetTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});



Ext.define("Zenoss.OverrideTemplatesDialog", {
    alias:['widget.overridetemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            title: _t('Override Templates'),
            listeners: {
                show: function() {
                    // completely reload the combobox every time
                    // we show the dialog
                    me.submit.setDisabled(true);
                    me.comboBox.setValue(null);
                    me.comboBox.store.setBaseParam('query', me.context);
                    me.comboBox.store.setBaseParam('uid', me.context);
                    me.comboBox.store.load();
                }
            },
            items: [{
                xtype: 'label',
                border: false,
                html: _t('Select the bound template you wish to override.')
            },{
                xtype: 'combo',
                forceSelection: true,
                emptyText: _t('Select a template...'),
                minChars: 0,
                ref: 'comboBox',
                selectOnFocus: true,
                typeAhead: true,
                valueField: 'uid',
                displayField: 'label',
                resizable: true,
                store: {
                    xtype: 'directstore',
                    ref:'store',
                    directFn: REMOTE.getOverridableTemplates,
                    fields: ['uid', 'label'],
                    root: 'data'
                },
                listeners: {
                    select: function(){
                        // disable submit if nothing is selected
                        me.submit.setDisabled(!me.comboBox.getValue());
                    }
                }
            }],
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                ref: '../submit',
                disabled: true,
                text: _t('Submit'),
                handler: function(){
                    var records, data, templateIds;
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        var templateUid = me.comboBox.getValue();
                        Zenoss.remote.TemplateRouter.copyTemplate({
                            uid: templateUid,
                            targetUid: me.context
                        }, refreshTemplateTree);
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                text: _t('Cancel')
            }]
        });
        Zenoss.OverrideTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


Ext.define("Zenoss.removeLocalTemplateDialog", {
    alias:['widget.removelocaltemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            title: _t('Remove Local Template'),
            listeners: {
                show: function() {
                    // completely reload the combobox every time
                    // we show the dialog
                    me.submit.setDisabled(true);
                    me.comboBox.setValue(null);
                    me.comboBox.store.setBaseParam('query', me.context);
                    me.comboBox.store.setBaseParam('uid', me.context);
                    me.comboBox.store.load();
                }
            },
            items: [{
                xtype: 'label',
                border: false,
                html: _t('Select the locally defined template you wish to remove.')
            },{
                xtype: 'combo',
                forceSelection: true,
                emptyText: _t('Select a template...'),
                minChars: 0,
                ref: 'comboBox',
                selectOnFocus: true,
                valueField: 'uid',
                displayField: 'label',
                typeAhead: true,
                store: {
                    xtype: 'directstore',
                    ref:'store',
                    directFn: REMOTE.getLocalTemplates,
                    fields: ['uid', 'label'],
                    root: 'data'
                },
                listeners: {
                    select: function(){
                        // disable submit if nothing is selected
                        me.submit.setDisabled(!me.comboBox.getValue());
                    }
                }
            }],
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                ref: '../submit',
                disabled: true,
                text: _t('Submit'),
                handler: function(){
                    var records, data, templateIds;
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        var templateUid = me.comboBox.getValue();
                        REMOTE.removeLocalTemplate({
                            deviceUid: me.context,
                            templateUid: templateUid
                        }, refreshTemplateTree);
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',                
                text: _t('Cancel')
            }]
        });
        Zenoss.OverrideTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


})();
