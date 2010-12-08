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

/* package level */
(function() {
    Ext.ns('Zenoss.form');
    Zenoss.form.SettingsGrid = Ext.extend(Zenoss.DeviceOverviewForm, {
        constructor: function(config, itemsConfig) {
            config = config || {};
            var i,
                me = this,
                prop;

            // build the properties and editors
            for (i=0; i < itemsConfig.length; i++){
                prop = itemsConfig[i];
                prop.fieldLabel = prop.name;
                if (!prop.value) {
                    prop.value = prop.defaultValue;
                }
                prop.ref = prop.id;
                prop.name = prop.id;
            }
            this.lastValues = itemsConfig;

            Ext.applyIf(config, {
                autoScroll: 'y',
                labelAlign: 'top',
                bodyStyle: 'padding: 10px',
                monitorValid: true,
                isDirty: function(){
                    return true;
                },
                buttons: [{
                    text: _t('Save'),
                    ref: '../savebtn',
                    hidden: true,
                    formBind: true,
                    handler: function(btn){
                        var values = {};
                        Ext.each(itemsConfig, function(prop){
                            values[prop.id] = me[prop.id].getValue();
                        });
                        config.saveFn({values: values}, function(response){
                            if (response.success){
                                var message = _t("Configuration updated");
                                Zenoss.message.info(message);
                                btn.setDisabled(true);
                                btn.refOwner.cancelbtn.setDisabled(true);
                            }
                        });
                    }
                },{
                    text: _t('Cancel'),
                    ref: '../cancelbtn',
                    hidden: true,
                    handler: function(btn) {
                        var form = btn.refOwner;
                        form.setInfo(form.lastValues);
                    }
                }],
                items: itemsConfig,
                setInfo: function(data) {
                    var me = this;
                    Ext.each(data, function(prop){
                        me[prop.id].setValue(prop.value);
                    });
                },

                autoHeight: true,
                viewConfig : {
                    forceFit: true
                }
            });
            Zenoss.form.SettingsGrid.superclass.constructor.apply(this, arguments);
        }
    });
    Ext.reg('settingsgrid', Zenoss.form.SettingsGrid);

}());


