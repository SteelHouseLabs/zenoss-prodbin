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
Ext.ns('Zenoss.ui.Reports');

Ext.onReady(function () {

var addtozenpack,
    report_panel = new Zenoss.BackCompatPanel({}),
    treesm,
    report_tree;

/*
 * Delete a report class
 */
function deleteNode(e) {
    report_tree.deleteSelectedNode();
}

/*
 * add report class to zenpack
 */
function addToZenPack(e) {
    if (!addtozenpack) {
        addtozenpack = new Zenoss.AddToZenPackWindow();
    }
    addtozenpack.setTarget(treesm.getSelectedNode().attributes.uid);
    addtozenpack.show();
}

function initializeTreeDrop(g) {
    var dz = new Ext.tree.TreeDropZone(g, {
        ddGroup: 'reporttreedd',
        appendOnly: true,
        onNodeDrop: function (target, dd, e, data) {
            var tree = this.tree,
                uid = data.node.attributes.uid,
                targetUid = target.node.attributes.uid;
            if (target.node.attributes.leaf || uid == targetUid) {
                return false;
            }
            Zenoss.remote.ReportRouter.moveNode({
                uid: uid,
                target: targetUid
            }, function (cb_data) {
                if (cb_data.success) {
                    data.node.parentNode.removeChild(data.node);
                    data.node.destroy();
                    insertNewNode(tree, cb_data, target.node);
                }
            });
            return true;
        }
    });
}

function insertNewNode(tree, data, organizerNode) {
    var newNode = tree.getLoader().createNode(data.newNode),
        firstLeafNode = organizerNode.findChild('leaf', true);
    organizerNode.expand();
    if (firstLeafNode) {
        organizerNode.insertBefore(newNode, firstLeafNode);
    } else {
        organizerNode.appendChild(newNode);
    }
    newNode.select();
    newNode.expand(true);
    tree.update(data.tree);
    return newNode;
}

Zenoss.ReportTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {
    addNode: function (nodeType, id) {
        var selNode = this.getSelectionModel().getSelectedNode(),
            parentNode = selNode.leaf ? selNode.parentNode : selNode,
            tree = this,
            newNode;
        this.router.addNode({
            nodeType: nodeType,
            contextUid: parentNode.attributes.uid,
            id: id
        }, function (data) {
            if (data.success) {
                newNode = insertNewNode(tree, data, parentNode);
                if (newNode.attributes.edit_url) {
                    window.location = newNode.attributes.edit_url;
                }
            }
        });
    },
    deleteSelectedNode: function () {
        var node = this.getSelectionModel().getSelectedNode();
        if (node.attributes.leaf) {
            this._confirmDeleteSelectedNode(_t('Delete Report'),
                _t('Confirm report deletion.'));
        } else {
            if (node.childNodes.length < 1) {
                this._deleteSelectedNode();
            } else {
                this._confirmDeleteSelectedNode(_t('Delete Organizer'),
                    _t('Warning! This will delete all of the reports in this group!'));
            }
        }
    },
    _confirmDeleteSelectedNode: function (title, message) {
        Ext.MessageBox.show({
            title: title,
            msg: message,
            fn: function(buttonid) {
                if (buttonid=='ok') {
                    report_tree._deleteSelectedNode();
                }
            },
            buttons: Ext.MessageBox.OKCANCEL
        });
    },
    _deleteSelectedNode: function () {
        var node = this.getSelectionModel().getSelectedNode(),
                parentNode = node.parentNode,
                uid = node.attributes.uid,
                params = {uid: uid},
                tree = this;
        function callback(data) {
            if (data.success) {
                parentNode.select();
                parentNode.removeChild(node);
                node.destroy();
                tree.update(data.tree);
                // the select() above is insufficient; 
                // the url refers to the deleted node still. 
                parentNode.fireEvent('click', parentNode);
            }
        }
        this.router.deleteNode(params, callback);
    },
    editReport: function () {
        window.location = this.getSelectionModel().getSelectedNode().attributes.edit_url;
    }
});

report_panel.addListener('frameloadfinished', function(win) {
    var anchors = win.document.getElementsByTagName('a');
    for (var idx = 0; idx < anchors.length; idx++) {
        if (!/\/zport\/dmd\/[rR]eports\//.test(anchors[idx].href)) {
            anchors[idx].onclick = function() {
                window.top.location.href = this.href;
            };
        }
    }
});

treesm = new Ext.tree.DefaultSelectionModel({
    listeners: {
        'selectionchange': function (sm, newnode) {
            if (newnode == null) {
                return;
            }
            var attrs = newnode.attributes;
            report_panel.setContext(attrs.leaf ? attrs.uid + '?adapt=false' : '');
            Ext.getCmp('add-organizer-button').setDisabled(attrs.leaf);
            Ext.getCmp('add-to-zenpack-button').setDisabled(attrs.leaf);
            Ext.getCmp('edit-button').setDisabled(!attrs.edit_url);
            Ext.getCmp('delete-button').setDisabled(!attrs.deletable);
        }
    }
});

report_tree = new Zenoss.ReportTreePanel({
    id: 'reporttree',
    cls: 'report-tree',
    ddGroup: 'reporttreedd',
    searchField: true,
    rootVisible: true,
    enableDD: true,
    directFn: Zenoss.remote.ReportRouter.asyncGetTree,
    router: Zenoss.remote.ReportRouter,
    root: {
        nodeType: 'async',
        id: '.zport.dmd.Reports',
        uid: '/zport/dmd/Reports',
        text: _t('Report Classes'),
        allowDrop: false
    },
    selModel: treesm,
    listeners: {
        render: initializeTreeDrop,
        click: function (node, e) {
            if (node.attributes.leaf) {
                report_panel.setContext(node.attributes.uid + '?adapt=false');
            }
        }
    },
    dropConfig: { appendOnly: true }
});

report_tree.expandAll();

var treepanel = {
    xtype: 'HierarchyTreePanelSearch',
    items: [report_tree]
};

Ext.getCmp('center_panel').add({
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border': false
    },
    items: [{
        id: 'master_panel',
        layout: 'fit',
        region: 'west',
        width: 300,
        split: true,
        items: [treepanel]
    }, {
        layout: 'fit',
        region: 'center',
        items: [report_panel]
    }]
});

function createAction(typeName, text) {
    return new Zenoss.Action({
        text: _t('Add ') + text + '...',
        iconCls: 'add',
        handler: function () {
            var addDialog = new Zenoss.FormDialog({
                title: _t('Create ') + text,
                modal: true,
                width: 310,
                formId: 'addForm',
                items: [{
                    xtype: 'textfield',
                    fieldLabel: _t('ID'),
                    name: 'name',
                    allowBlank: false
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('Submit'),
                    handler: function () {
                        var form, newName;
                        form = Ext.getCmp('addForm').getForm();
                        newName = form.findField('name').getValue();
                        report_tree.addNode(typeName, newName);
                    }
                },
                    Zenoss.dialog.CANCEL
                ]
            });
            addDialog.show(this);
        }
    });
}

Ext.getCmp('footer_bar').add({
    id: 'add-organizer-button',
    tooltip: _t('Add report organizer or report'),
    iconCls: 'add',
    menu: {
        width: 190, // mousing over longest menu item was changing width
        items: [
            createAction('organizer', _t('Report Organizer'))
        ]
    }
});

Zenoss.remote.ReportRouter.getReportTypes({},
    function (data) {
        var menu = Ext.getCmp('add-organizer-button').menu;
        for (var idx = 0; idx < data.reportTypes.length; idx++) {
            var reportType = data.reportTypes[idx],
                    menuText = data.menuText[idx];
            menu.add(createAction(reportType, menuText));
        }
    }
);

Ext.getCmp('footer_bar').add({
    id: 'delete-button',
    tooltip: _t('Delete an item'),
    iconCls: 'delete',
    handler: deleteNode
});

Ext.getCmp('footer_bar').add({
    xtype: 'tbseparator'
});

Ext.getCmp('footer_bar').add({
    id: 'edit-button',
    tooltip: _t('Edit a report'),
    iconCls: 'set',
    handler: function() {
        report_tree.editReport();
    }
});

Ext.getCmp('footer_bar').add({
    id: 'add-to-zenpack-button',
    tooltip: _t('Add to ZenPack'),
    iconCls: 'adddevice',
    handler: addToZenPack
});

});
