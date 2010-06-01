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

var router, treeId, initTreeDialogs;

router = Zenoss.remote.TemplateRouter;
treeId = 'templateTree';

initTreeDialogs = function(tree) {

    new Zenoss.HideFormDialog({
        id: 'addTemplateDialog',
        title: _t('Add Monitoring Template'),
        items: {
            xtype: 'textfield',
            id: 'idTextfield',
            fieldLabel: _t('Name'),
            allowBlank: false
        },
        listeners: {
            'hide': function(treeDialog) {
                Ext.getCmp('idTextfield').setValue('');
            }
        },
        buttons: [
            {
                xtype: 'HideDialogButton',
                text: _t('Submit'),
                handler: function(button, event) {
                    var id = Ext.getCmp('idTextfield').getValue();
                    tree.addTemplate(id);
                }
            }, {
                xtype: 'HideDialogButton',
                text: _t('Cancel')
            }
        ]
    });

    new Zenoss.MessageDialog({
        id: 'deleteNodeDialog',
        title: _t('Delete Tree Node'),
        message: _t('The selected node will be deleted.'),
        okHandler: function(){
            tree.deleteTemplate();
        }
    });

};

Ext.ns('Zenoss');

/**
 * @class Zenoss.TemplateTreePanel
 * @extends Ext.tree.TreePanel
 * @constructor
 */
Zenoss.TemplateTreePanel = Ext.extend(Ext.tree.TreePanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            id: treeId,
            rootVisible: false,
            border: false,
            autoScroll: true,
            containerScroll: true,
            useArrows: true,
            cls: 'x-tree-noicon',
            loader: {
                directFn: router.getTemplates,
                baseAttrs: {singleClickExpand: true}
            },
            root: {
                nodeType: 'async',
                id: 'root'
            },
            listeners: {
                scope: this,
                expandnode: this.onExpandnode
            }
        });
        Zenoss.TemplateTreePanel.superclass.constructor.call(this, config);
        initTreeDialogs(this);
        this.on('buttonClick', this.buttonClickHandler, this);
    },
    buttonClickHandler: function(buttonId) {
        switch(buttonId) {
            case 'addButton':
                Ext.getCmp('addTemplateDialog').show();
                break;
            case 'deleteButton':
                Ext.getCmp('deleteNodeDialog').show();
                break;
            default:
                break;
        }
    },
    
    addTemplate: function(id) {
        var rootNode, contextUid, params, tree, type;
        rootNode = this.getRootNode();
        contextUid = rootNode.attributes.uid;
        params = {contextUid: contextUid, id: id};
        tree = this;
        function callback(provider, response) {
            var result, nodeConfig, node, leaf;
            result = response.result;
            if (result.success) {
                nodeConfig = response.result.nodeConfig;
                node = tree.getLoader().createNode(nodeConfig);
                rootNode.appendChild(node);
                node.expand();
                leaf = node.childNodes[0];
                leaf.select();
            } else {
                Ext.Msg.alert('Error', result.msg);
            }
        }
        router.addTemplate(params, callback);
    },

    deleteTemplate: function() {
        var node, params, me;
        node = this.getSelectionModel().getSelectedNode();
        params = {uid: node.attributes.uid};
        me = this;
        function callback(provider, response) {
            me.getRootNode().reload();
        }
        router.deleteTemplate(params, callback);
    },
    afterRender: function() {
        Zenoss.TemplateTreePanel.superclass.afterRender.call(this);
        
        // add the search text box
        this.add({
            xtype: 'searchfield',
            ref: 'searchField',
            bodyStyle: {padding: 10},
            listeners: {
                valid: this.filterTree,
                scope: this
            }
        });
    },
                                        
    clearFilter: function() {
        // use set raw value to not trigger listeners
        this.searchField.setRawValue('');
        this.hiddenPkgs = [];
    },
                                          
    filterTree: function(e) {
        var re,
            text = e.getValue();
        
        // show all of our hidden nodes
        if (this.hiddenPkgs) {
            Ext.each(this.hiddenPkgs, function(node){node.ui.show();});
        }

        // de-select the selected node
        if (this.getSelectionModel().getSelectedNode()){
            this.getSelectionModel().getSelectedNode().unselect();  
        }
        
        this.hiddenPkgs = [];
        if (!text) {
            return;
        }
        this.expandAll();

        // test every node against the Regular expression
        re = new RegExp(Ext.escapeRe(text), 'i');
        this.root.cascade(function(node){
            var attr = node.id, parentNode;
            if (!node.isRoot) {
                if (re.test(attr)) {
                    // if regex passes show our node and our parent
                    parentNode = node.parentNode;
                    while (parentNode) {
                        if (!parentNode.hidden) {
                            break;
                        }
                        parentNode.ui.show();
                        parentNode = parentNode.parentNode;
                    }
                    // the cascade is stopped on this branch
                    return false;
                } else {
                    node.ui.hide();
                    this.hiddenPkgs.push(node);
                }
            }
            // continue cascading down the tree from this node
            return true;
        }, this);
    },
    
    onExpandnode: function(node) {
        // select the first template when the base URL is accessed without a
        // history token and without a filter value
        if ( ! this.searchField.getValue() && ! Ext.History.getToken() ) {
            if ( node === this.getRootNode() ) {
                node.childNodes[0].expand();
            } else {
                node.childNodes[0].select();
            }
        }
    },
    
    selectByToken: function(uid) {
        // called on Ext.History change event (see HistoryManager.js)
        // convert uid to path and select the path
        // example uid: '/zport/dmd/Devices/Power/UPS/APC/rrdTemplates/Device'
        // example path: '/root/Device/Device..Power.UPS.APC'
        var uidParts, templateName, dmdPath, path;
        uidParts = unescape(uid).split('/');
        templateName = uidParts[uidParts.length - 1];

        if ( uidParts.length === 6 ) {
            // Defined at devices, special case, include 'Devices'
            dmdPath = 'Devices';
        } else {
            // all the DeviceClass names under Devices separated by dots
            dmdPath = uidParts.slice(4, uidParts.length - 2).join('.');
        }
        path = String.format('/root/{0}/{0}..{1}', templateName, dmdPath);
        this.selectPath(path);
    }
    
});

Ext.reg('TemplateTreePanel', Zenoss.TemplateTreePanel);

})();
