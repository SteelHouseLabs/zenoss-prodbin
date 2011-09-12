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

Ext.onReady(function() {

    var EventAgeSeverity;
    var AGE_ALL_EVENTS = 6;

    EventAgeSeverity = Ext.extend(Ext.form.ComboBox, {
        constructor: function(config) {
            config = config || {};
            var store = [[AGE_ALL_EVENTS, _t('Age All Events')]].concat(Zenoss.env.SEVERITIES);
            Ext.applyIf(config, {
                fieldLabel: _t('Severity'),
                name: 'severity',
                editable: false,
                forceSelection: true,
                autoSelect: true,
                triggerAction: 'all',
                mode: 'local',
                store: store
            });
            EventAgeSeverity.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('eventageseverity', EventAgeSeverity);

    Ext.ns('Zenoss.settings');
    var router = Zenoss.remote.EventsRouter;


    function saveConfigValues(results, callback) {
        // if they wish to age all events update the inclusive flag
        var values = results.values;
        values.event_age_severity_inclusive = false;
        if (values.event_age_disable_severity == AGE_ALL_EVENTS) {
            values.event_age_disable_severity = 5; // critical
            values.event_age_severity_inclusive = true;
        }
        router.setConfigValues(results, callback);
    }

    function buildPropertyGrid(response) {
        var propsGrid,
            severityField, inclusiveField,
            data;
        data = response.data;
        severityField = Zenoss.util.filter(data, function(field) {
            return field.id == 'event_age_disable_severity';
        })[0];

        inclusiveField = Zenoss.util.filter(data, function(field) {
            return field.id == 'event_age_severity_inclusive';
        })[0];

        if (inclusiveField.value) {
            // set the dropdown box to include the selected severity (if it is critical,
            // then the drop down will show "Age All Events")
            severityField.value = severityField.value + 1;
        }
        propsGrid = new Zenoss.form.SettingsGrid({
            renderTo: 'propList',
            width: 500,
            saveFn: saveConfigValues
        }, data);
    }

    function loadProperties() {
        router.getConfig({}, buildPropertyGrid);
    }

    loadProperties();

    var clearHeartbeatPanel = new Ext.Panel({
        renderTo: 'clearHeartbeat',
        layout: 'hbox',
        layoutConfig: {
            pack: 'center',
            align: 'middle'
        },
        bodyStyle: 'background-color: #FAFAFA; border-style: none solid none solid;',
        width: 500,
        padding: 10,
        items: [
            {
                xtype: 'button',
                text: _t('Clear'),
                handler: function() {
                    var confirmDialog = new Zenoss.MessageDialog({
                        title: _t('Clear Heartbeats'),
                        message: _t('Clear all heartbeat events? This cannot be undone.'),
                        okHandler: function() {
                            router.clear_heartbeats({}, function(response) {
                                if (response.success) {
                                    Zenoss.message.success(_t('Heartbeat events succesfully deleted.'));
                                }
                                else {
                                    Zenoss.message.error(_t('Error deleting heartbeat events.'));
                                }
                            });
                        }
                    });
                    confirmDialog.show();
                }
            }, {
                xtype: 'spacer',
                width: 10
            }, {
                html: _t('Clear all heartbeat events'),
                bodyStyle: 'font-size:110%; font-color: #5A5A5A;'
            }
        ]
    });

});