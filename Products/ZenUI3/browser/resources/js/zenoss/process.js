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

// Script for the processes page.

Ext.onReady(function(){

Ext.ns('Zenoss', 'Zenoss.env');
var treeId = 'processTree';
var router = Zenoss.remote.ProcessRouter;

new Zenoss.MessageDialog({
    id: 'dirtyDialog',
    title: _t('Unsaved Data'),
    message: _t('The changes made in the form will be lost.'),
    okHandler: function() {
        Ext.getCmp('processForm').getForm().reset();
        Zenoss.env.node.select();
    }
});

/* ***************************************************************************
 *
 *   master_panel - the processes tree on the left
 *
 */

function beforeselectHandler(sm, node, oldNode) {
    if (node == oldNode) {
        return false;
    }
    if ( Ext.getCmp('processForm').getForm().isDirty() ) {
        // the user made changes to the form make sure that they don't care
        // about losing those changes
        Zenoss.env.node = node;
        Ext.getCmp('dirtyDialog').show();
        return false;
    }
    return true;
}

// function that gets run when the user clicks on a node in the tree
function selectionchangeHandler(sm, node) {
    if (node) {
        // load up appropriate data in the form
        Ext.getCmp('processForm').getForm().load({
            params: {uid: node.attributes.uid}
        });
        Ext.getCmp('instancesGrid').setContext(node.attributes.uid);
        // don't allow the user to delete the root node
        Ext.getCmp('deleteButton').setDisabled(node == Ext.getCmp(treeId).root);
    }
}

var selModel = new Ext.tree.DefaultSelectionModel({
    listeners: {
        beforeselect: beforeselectHandler,
        selectionchange: selectionchangeHandler
    }
});

Ext.getCmp('master_panel').add({
    xtype: 'HierarchyTreePanel',
    id: treeId,
    searchField: true,
    directFn: router.getTree,
    router: router,
    selModel: selModel,
    root: {
        id: 'Processes',
        uid: '/zport/dmd/Processes'
    }
}); // master_panel.add


/* **************************************************************************
 *
 *   top_detail_panel - the process form on the top right
 *
 */


// disable the monitoring fields if monitoring settings are inherited
function  setMonitoringDisabled(disabled) {
    var monitorCheckbox = Ext.getCmp('monitorCheckbox');
    var eventSeverityCombo = Ext.getCmp('eventSeverityCombo');
    monitorCheckbox.setDisabled(disabled);
    eventSeverityCombo.setDisabled(disabled);
}

function inheritedCheckboxHandler(checkbox, checked) {
    setMonitoringDisabled(checked);
    var processTree = Ext.getCmp(treeId);
    var selectionModel = processTree.getSelectionModel();
    var selectedNode = selectionModel.getSelectedNode();

    var uid;
    if (checked && selectedNode.parentNode !== null) {
        uid = selectedNode.parentNode.attributes.uid;
    } else {
        uid = selectedNode.attributes.uid;
    }

    var callback = function(provider, response) {
        var info = response.result.data;
        var monitorCheckbox = Ext.getCmp('monitorCheckbox');
        monitorCheckbox.setValue(info.monitor);
        var eventSeverityCombo = Ext.getCmp('eventSeverityCombo');
        eventSeverityCombo.setValue(info.eventSeverity);
    };

    router.getInfo({uid: uid, keys: ['monitor', 'eventSeverity']}, callback);
}

// when the form loads, show/hide the regex fieldset
function actioncompleteHandler(form, action) {
    if (action.type == 'directload') {
        var processInfo = action.result.data;
        var regexFieldSet = Ext.getCmp('regexFieldSet');
        var nameTextField = Ext.getCmp('nameTextField');
        var inheritedCheckbox = Ext.getCmp('inheritedCheckbox');
        regexFieldSet.setVisible(processInfo.hasRegex);
        regexFieldSet.doLayout();
        nameTextField.setDisabled(processInfo.name == 'Processes');
        inheritedCheckbox.setDisabled(processInfo.name == 'Processes');
        setMonitoringDisabled(processInfo.isMonitoringAcquired);
        Ext.getCmp('processForm').setDisabled(action.result.disabled);
    }
}

var nameTextField = {
    xtype: 'textfield',
    id: 'nameTextField',
    fieldLabel: _t('Name'),
    name: 'name',
    allowBlank: false,
    width: "100%"
};

var descriptionTextField = {
    xtype: 'textfield',
    fieldLabel: _t('Description'),
    name: 'description',
    width: "100%"
};

var inheritedCheckbox = {
    xtype: 'checkbox',
    id: 'inheritedCheckbox',
    fieldLabel: _t('Inherited'),
    name: 'isMonitoringAcquired',
    handler: inheritedCheckboxHandler
};

var monitorCheckbox = {
    xtype: 'checkbox',
    id: 'monitorCheckbox',
    fieldLabel: _t('Enabled'),
    name: 'monitor'
};

var eventSeverityCombo = {
    xtype: 'combo',
    id: 'eventSeverityCombo',
    fieldLabel: _t('Event Severity'),
    name: 'eventSeverity',
    triggerAction: 'all',
    mode: 'local',
    valueField: 'severityId',
    displayField: 'severityText',
    store: new Ext.data.ArrayStore({
        fields: ['severityId', 'severityText'],
        data: Zenoss.env.SEVERITIES.slice(0, 5)
    })
};

var regexTextField = {
    xtype: 'textfield',
    id: 'regexTextField',
    fieldLabel: _t('Pattern'),
    name: 'regex',
    width: "100%"
};

var ignoreParametersCheckbox = {
    xtype: 'checkbox',
    id: 'ignoreParametersCheckbox',
    fieldLabel: _t('Ignore Parameters'),
    name: 'ignoreParameters'
};

var monitoringFieldSet = {
    xtype: 'ColumnFieldSet',
    title: _t('Monitoring'),
    __inner_items__: [
        {
            items: inheritedCheckbox
        }, {
            items: monitorCheckbox,
            bodyStyle: 'padding-left: 15px'
        }, {
            items: eventSeverityCombo,
            bodyStyle: 'padding-left: 15px'
        }
    ]
}; // monitoringFieldSet

var regexFieldSet = {
    xtype: 'ColumnFieldSet',
    id: 'regexFieldSet',
    title: _t('Regular Expression'),
    hidden: true,
    __inner_items__: [
        {
            items: regexTextField,
            columnWidth: 0.6
        }, {
            items: ignoreParametersCheckbox,
            bodyStyle: 'padding-left: 15px'
        }
    ]
}; // regexFieldSet

// the items that make up the form
var processFormItems = {
    layout: 'column',
    border: false,
    defaults: {
        layout: 'form',
        border: false,
        bodyStyle: 'padding: 15px',
        labelSeparator: ' ',
        columnWidth: 0.5
    },
    items: [
        {items: [nameTextField, monitoringFieldSet]},
        {items: [descriptionTextField, regexFieldSet]}
    ]
}; // processFormItems

var processFormConfig = {
    xtype: 'form',
    id: 'processForm',
    paramsAsHash: true,
    items: processFormItems,
    border: false,
    labelAlign: 'top',
    autoScroll: true,
    api: {
        load: router.getInfo,
        submit: router.setInfo
    },
    tbar: [
        {
            xtype: 'button',
            id: 'saveButton',
            text: _t('Save'),
            iconCls: 'save',
            handler: function(button, event) {
                var processTree = Ext.getCmp(treeId);
                var selectionModel = processTree.getSelectionModel();
                var selectedNode = selectionModel.getSelectedNode();
                var nameTextField = Ext.getCmp('nameTextField');
                selectedNode.attributes.text.text = nameTextField.getValue();
                selectedNode.setText(selectedNode.attributes.text);
                var form = Ext.getCmp('processForm').getForm();
                var params = Ext.apply({uid: selectedNode.attributes.uid},
                                       form.getValues());
                form.api.submit(params);
                // setValues makes isDirty return false
                form.setValues(form.getValues());
            }
        }, {
            xtype: 'button',
            id: 'cancelButton',
            text: _t('Cancel'),
            iconCls: 'close',
            handler: function(button, event) {
                Ext.getCmp('processForm').getForm().reset();
            }
        }
    ] //tbar
};

Ext.ns('Zenoss');

/**
 * @class Zenoss.ProcessFormPanel
 * @extends Ext.form.FormPanel
 * The form panel that displays information about a process organizer or class
 * @constructor
 */
Zenoss.ProcessFormPanel = Ext.extend(Ext.form.FormPanel, {

    constructor: function(userConfig) {
        var config = Ext.apply(processFormConfig, userConfig);
        Zenoss.ProcessFormPanel.superclass.constructor.call(this, config);
        this.on('actioncomplete', actioncompleteHandler);
    }

});

Ext.reg('ProcessFormPanel', Zenoss.ProcessFormPanel);

var processForm = new Zenoss.ProcessFormPanel({
    trackResetOnLoad: true
});

// place the form in the top right
Ext.getCmp('top_detail_panel').add(processForm);

processForm.getForm().load({params:{uid: 'Processes'}});


/* ***********************************************************************
 *
 *   bottom_detail_panel - the device and event grid on the bottom right
 *
 */
Ext.getCmp('bottom_detail_panel').add({
    xtype: 'SimpleDeviceGridPanel',
    id: 'instancesGrid',
    directFn: router.getDevices
});


/* ***********************************************************************
 *
 *   footer_panel - the add/remove tree node buttons at the bottom
 *
 */
var footerPanel = Ext.getCmp('footer_panel');
footerPanel.removeAll();

footerPanel.add({
    xtype: 'TreeFooterBar',
    id: 'footer_bar',
    bubbleTargetId: treeId
});

Ext.getCmp('deleteButton').setDisabled(true);

}); // Ext.onReady
