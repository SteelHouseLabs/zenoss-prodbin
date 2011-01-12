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
Ext.ns('Zenoss.ui.EvConsole');

Ext.onReady(function(){
    // Global dialogs, will be reused after first load
    var win,
        addevent,
        configwin,
    // Date renderer object, used throughout
        date_renderer = Ext.util.Format.dateRenderer(Zenoss.date.ISO8601Long),
    // Get references to the panels
        detail_panel = Ext.getCmp('detail_panel'),
        master_panel = Ext.getCmp('master_panel');

    master_panel.layout = 'border';

    // Make this instance of the detail panel use a unique state ID so
    // it doesn't interfere with the state of other instances of this panel.
    detail_panel.stateId = 'Zenoss.ui.EvConsole.detail_panel';

    // Make the detail panel collapsible
    detail_panel.animCollapse = false;
    detail_panel.collapsible =false;
    detail_panel.collapsed = true;

    /*
     * Assemble the parameters that define the grid state.
     */
    function getQueryParameters() {
        var grid = Ext.getCmp('events_grid'),
            sortInfo = grid.view.ds.sortInfo;
        grid.view.applyFilterParams({'params':sortInfo});
        return sortInfo;
    }

    /*
     * Assemble the parameters that define the records selected. This by
     * necessity includes query parameters, since ranges need row indices.
     */
    function getSelectionParameters() {
        var grid = Ext.getCmp('events_grid'),
            sm = grid.getSelectionModel(),
            ranges = sm.getPendingSelections(true),
            evids = [],
            sels = sm.getSelections();
        
        if (sm.selectState == 'All') {
            // If we are selecting all, we don't want to send back any evids.
            // this will make the operation happen on the filter's result
            // instead of whatever the view seems to have selected.
            sels = [];
        }
        Ext.each(sels, function(record){
            evids[evids.length] = record.data.evid;
        });
        if (!ranges && !evids) return false;
        var params = {
            evids:evids,
            excludeIds: sm.badIds,
            selectState: sm.selectState
        };
        Ext.apply(params, getQueryParameters());
        return params;
    }

    /*
     * Show the dialog that allows one to add an event.
     */
    function showAddEventDialog() {
        if(!addevent){
        addevent = new Ext.Window({
            title: 'Create Event',
            layout: 'fit',
            autoHeight: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            items: [{
                id: 'addeventform',
                xtype: 'form',
                monitorValid: true,
                defaults: {width: 180},
                autoHeight: true,
                border: false,
                frame: false,
                labelWidth: 100,
                items: [{
                    xtype: 'textarea',
                    name: 'summary',
                    fieldLabel: 'Summary',
                    allowBlank: false
                },{
                    xtype: 'textfield',
                    fieldLabel: 'Device',
                    name: 'device',
                    allowBlank: false
                },{
                    xtype: 'textfield',
                    fieldLabel: 'Component',
                    name: 'component'
                },{
                    fieldLabel: 'Severity',
                    name: 'severity',
                    xtype: 'combo',
                    store: Zenoss.env.SEVERITIES,
                    typeAhead: true,
                    allowBlank: false,
                    forceSelection: true,
                    triggerAction: 'all',
                    value: 5,
                    selectOnFocus: true
                },{
                    xtype: 'textfield',
                    fieldLabel: 'Event Class Key',
                    name: 'evclasskey'
                },{
                    fieldLabel: 'Event Class',
                    name: 'evclass',
                    xtype: 'combo',
                    store: Zenoss.env.EVENT_CLASSES,
                    typeAhead: true,
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true
                }],
                buttons: [{
                    text: 'Submit',
                    formBind: true,
                    handler: function(){
                        var form = Ext.getCmp('addeventform');
                        Zenoss.remote.EventsRouter.add_event(
                            form.getForm().getValues(),
                            function(){
                                addevent.hide();
                                grid = Ext.getCmp('events_grid');
                                view = grid.getView();
                                view.updateLiveRows(
                                    view.rowIndex, true, true);
                            }
                        );
                    }
                },{
                    text: 'Cancel',
                    handler: function(){
                        addevent.hide();
                    }
                }]
            }]

        });
        }
        addevent.show(this);
    }

    /*
     * Show the dialog that allows one to add an event.
     */
    function showClassifyDialog(e) {
        if(!win){
            win = new Ext.Window({
                title: _t('Classify Events'),
                width: 300,
                autoHeight: true,
                closeAction: 'hide',
                plain: true,
                items: [{
                    id: 'classifyEventForm',
                    xtype: 'form',
                    monitorValid: true,
                    autoHeight: true,
                    border: false,
                    frame: false,
                    items: [{
                        padding: 10,
                        style: {'font-size':'10pt'},
                        html: _t('Select the event class with which'+
                            ' you want to associate these events.')
                    },{
                        xtype: 'combo',
                        store: Zenoss.env.EVENT_CLASSES,
                        typeAhead: true,
                        allowBlank: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        emptyText: _t('Select an event class'),
                        selectOnFocus: true,
                        id: 'evclass_combo'
                    }],
                    buttons: [{
                        text: _t('Submit'),
                        formBind: true,
                        disabled: true,
                        handler: function(){
                            var cb = Ext.getCmp('evclass_combo'),
                            sm = grid.getSelectionModel(),
                            rs = sm.getSelections(),
                            evrows = [];
                            Ext.each(rs, function(record){
                                evrows[evrows.length] = record.data;
                            });
                            if (!evrows.length) {
                                win.hide();
                                Ext.Msg.show({
                                    title: 'Error',
                                    msg: _t('No events were selected.'),
                                    buttons: Ext.MessageBox.OK
                                });
                            } else {
                                Zenoss.remote.EventsRouter.classify({
                                    'evclass': cb.getValue(),
                                    'evrows': evrows
                                }, function(result){
                                    win.hide();
                                    var title = result.success ?
                                        _t('Classified'):
                                        _t('Error');
                                    Ext.MessageBox.show({
                                        title: title,
                                        msg: result.msg,
                                        buttons: Ext.MessageBox.OK
                                    });
                                });
                            }
                        }
                    },{
                        text: _t('Cancel'),
                        handler: function(){
                            win.hide();
                        }
                    }
                             ]
                }]

            });
        }
        win.show(this);
    }

    /*
     * Select all events with a given state.
     * This requires a call to the back end, since we don't know anything about
     * records that are outside the current buffer. So we let the server
     * perform a query to determine ranges, then we select the ranges.
     */
    function selectByState(state) {
        var params = {'state':state, 'asof':Zenoss.env.asof},
            grid = Ext.getCmp('events_grid');
        Ext.apply(params, getQueryParameters());
        Zenoss.remote.EventsRouter.state_ranges(
            params,
            function(result) {
                var sm = grid.getSelectionModel();
                sm.clearSelections();
                Ext.each(result, function(range){
                    if (range.length==1)
                        range[1] = grid.getStore().totalLength + 1;
                   sm.selectRange(range[0]-1, range[1]-1, true);
                });
            }
        );
    }
    
    // Get the container surrounding master/detail, for adding the toolbar
    var container = Ext.getCmp('center_panel_container');
    
    // Add a CSS class to scope some styles that affect other parts of the UI
    container.on('render', function(){container.el.addClass('zenui3');});
    
    var eam = new Zenoss.EventActionManager({
        grid: 'events_grid'
    });
    
    // Add the toolbar to the container
    var tbar = new Zenoss.LargeToolbar({
            region:'north',
            border: false,
            items: [{
                /*
                 * ACKNOWLEDGE BUTTON
                 */
                //text: 'Acknowledge',
                iconCls: 'acknowledge',
                id: 'ack-button',
                handler: function() {
                    // Get params describing selected events
                    var params = getSelectionParameters();
                    if (params) {
                        eam.execute(Zenoss.remote.EventsRouter.acknowledge, params);
                    }
                }
            },{
                /*
                 * CLOSE BUTTON
                 */
                //text: 'Close',
                iconCls: 'close',
                id: 'close-button',
                handler: function(){
                    // Get params describing selected events
                    var params = getSelectionParameters();
                    if (params) {
                        eam.execute(Zenoss.remote.EventsRouter.close, params);
                    }
                }
            },{
                /*
                 * ClASSIFY BUTTON
                 */
                //text: 'Classify',
                id: 'classify-button',
                iconCls: 'classify',
                handler: showClassifyDialog
            },{
                //text: 'Unacknowledge',
                id: 'unack-button',
                iconCls: 'unacknowledge',
                handler: function() {
                    var params = getSelectionParameters();
                    if (params) {
                        eam.execute(Zenoss.remote.EventsRouter.reopen, params);
                    }
                }
            },{
                /*
                 * ADD BUTTON
                 */
                // text: _t('Add'),
                id: 'add-button',
                iconCls: 'add',
                handler: showAddEventDialog
            },{
                xtype: 'tbseparator'
            },
                Zenoss.events.SelectMenu,
            {
                text: _t('Export'),
                id: 'export-button',
                //iconCls: 'export',
                menu: {
                    items: [{
                        text: 'XML',
                        handler: function(){
                            var state = Ext.getCmp('events_grid').getState(),
                                params = {
                                    type: 'xml',
                                    params: {
                                        fields: Ext.pluck(state.columns, 'id'),
                                        sort: state.sort.field,
                                        dir: state.sort.direction,
                                        params: state.filters.options
                                    }
                                };
                            Ext.get('export_body').dom.value =
                                Ext.encode(params);
                            Ext.get('exportform').dom.submit();
                        }
                    }, {
                        text: 'CSV',
                        handler: function(){
                            var state = Ext.getCmp('events_grid').getState(),
                                params = {
                                    type: 'csv',
                                    params: {
                                        fields: Ext.pluck(state.columns, 'id'),
                                        sort: state.sort.field,
                                        dir: state.sort.direction,
                                        params: state.filters.options
                                    }
                                };
                            Ext.get('export_body').dom.value =
                                Ext.encode(params);
                            Ext.get('exportform').dom.submit();
                        }
                    }]
                }
            },{
                /*
                 * CONFIGURE MENU
                 */
                text: _t('Configure'),
                id: 'configure-button',
                //iconCls: 'customize',
                menu: {
                    items: [{
                        id: 'rowcolors_checkitem',
                        xtype: 'menucheckitem',
                        text: 'Show severity row colors',
                        handler: function(checkitem) {
                            var checked = !checkitem.checked;
                            var view = Ext.getCmp('events_grid').getView();
                            view.toggleRowColors(checked);
                        }
                    },{
                        id: 'livesearch_checkitem',
                        checked: true,
                        xtype: 'menucheckitem',
                        text: 'Enable live search',
                        handler: function(checkitem) {
                            var checked = !checkitem.checked;
                            var view = Ext.getCmp('events_grid').getView();
                            view.toggleLiveSearch(checked);
                        }
                    },{
                        id: 'clearfilters',
                        text: 'Clear filters',
                        listeners: {
                            click: function(){
                                grid.clearFilters();
                            }
                        }
                    },/*{
                        id: 'showfilters',
                        text: 'Show filters',
                        checked: false,
                        listeners: {
                            'checkchange' : function(ob, on) {
                                if(on) grid.showFilters()
                                else grid.hideFilters()
                            }
                        }
                    },*/{
                        text: 'Save this configuration...',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                                link = grid.getPermalink();
                           Ext.Msg.show({
                            title: 'Permalink',
                            msg: '<'+'div class="dialog-link">'+
                            'Drag this link to your bookmark' +
                            ' bar <'+'br/>to return to this grid '+
                             'configuration later.'+
                             '<'+'br/><'+'br/><'+'a href="'+
                             link + '">'+
                             'Event Console<'+'/a><'+'/div>',
                            buttons: Ext.Msg.OK
                            });
                        }
                    },{
                        text: "Restore defaults",
                        handler: function(){
                            Ext.Msg.show({
                                title: 'Confirm Restore',
                                msg: 'Are you sure you want to restore '+
                                  'the default grid configuration? All' +
                                  ' filters, column sizing, and column order '+
                                  'will be lost.',
                                buttons: Ext.Msg.OKCANCEL,
                                fn: function(val){
                                    if (val=='ok')
                                        Ext.getCmp('events_grid').resetGrid();
                                }
                            });
                        }
                    }]
                }
            },{
                xtype: 'tbfill'
            },{
                id: 'lastupdated',
                xtype: 'tbtext',
                cls: 'lastupdated',
                text: 'Updating...'
            },{
                xtype: 'refreshmenu',
                ref: 'refreshmenu',
                id: 'refresh-button',
                iconCls: 'refresh',
                text: _t('Refresh'),
                handler: function(){
                    view = Ext.getCmp('events_grid').getView();


                    view.updateLiveRows(view.rowIndex, true, true);
                }
            }
            ]
        });

    function doLastUpdated() {
        var box = Ext.getCmp('lastupdated'),
            dt = new Date(),
            dtext = dt.format('g:i:sA');
            box.setText(_t('Last updated at ') + dtext);
    };

    // View to render the grid
    var myView = new Zenoss.FilterGridView({
        nearLimit : 20,
        filterbutton: 'showfilters',
        defaultFilters: {
            severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
            eventState: [Zenoss.STATUS_NEW, Zenoss.STATUS_ACKNOWLEDGED],
            // _managed_objects is a global function sent from the server, see ZenUI3/security/security.py
            tags: _managed_objects()
        },
        rowcoloritem: 'rowcolors_checkitem',
        livesearchitem: 'livesearch_checkitem',
        loadMask  : { msg :  'Loading. Please wait...' }
    });

    function disableEventConsoleButtons() {
        var disabled = Zenoss.Security.doesNotHavePermission('Manage Events');
        var buttonIds = [
            'ack-button',
            'close-button',
            'classify-button',
            'unack-button',
            'add-button'
        ];
        Ext.each(buttonIds, function(buttonId) {
            var button = Ext.getCmp(buttonId);
            button.setDisabled(disabled);
        });
    }

    var console_store = new Zenoss.EventStore({
        autoLoad: true,
        proxy: new Zenoss.ThrottlingProxy({
            directFn: Zenoss.remote.EventsRouter.query,
            listeners: {
                'load': function(proxy, transaction, options) {
                   disableEventConsoleButtons();
                }}
        })
    });

    // if the user has no global roles and does not have any admin. objects
    // do not show any events.
    if (!_has_global_roles() && _managed_objects().length == 0){
        console_store = new Ext.ux.grid.livegrid.Store({});
        disableEventConsoleButtons();
    }

    // Selection model
    var console_selection_model = new Zenoss.EventPanelSelectionModel();

    /*
     * THE GRID ITSELF!
     */
    var grid = new Zenoss.FilterGridPanel({
        region: 'center',
        tbar: tbar,
        id: 'events_grid',
        stateId: Zenoss.env.EVENTSGRID_STATEID,
        enableDragDrop: false,
        stateful: true,
        border: false,
        rowSelectorDepth: 5,
        autoExpandColumn: Zenoss.env.EVENT_AUTO_EXPAND_COLUMN || '',
        store: console_store, // defined above
        view: myView, // defined above
        // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
        // the resultFields associated with the context.
        cm: new Zenoss.FullEventColumnModel(),
        stripeRows: true,
        // Map some other keys
        keys: [{
        // Enter to pop open the detail panel
            key: Ext.EventObject.ENTER,
            fn: toggleEventDetailContent
        }],
        sm: console_selection_model // defined above
    });
    // Add it to the layout
    master_panel.add(grid);

    var pageParameters = Ext.urlDecode(window.location.search.substring(1));
    if (pageParameters.filter === "default") {
        // reset eventconsole filters to the default
        grid.resetGrid();
    }

    /*
     * DETAIL PANEL STUFF
     */
    // Pop open the event detail, depending on the number of rows selected
    function toggleEventDetailContent(){
        var count = console_selection_model.getCount();
        if (count==1) {
            showEventDetail(console_selection_model.getSelected());
        } else {
            wipeEventDetail();
        }
    }

    // Pop open the event detail pane and populate it with the appropriate data
    // and switch triggers (single select repopulates detail, esc to close)
    function showEventDetail(r) {
        Ext.getCmp('dpanelcontainer').load(r.data.evid);
        grid.un('rowdblclick', toggleEventDetailContent);
        detail_panel.expand();
        esckeymap.enable();
    }

    // Wipe event detail values
    function wipeEventDetail() {
        Ext.getCmp('dpanelcontainer').wipe();
    }

    // Collapse the event detail pane and switch triggers (double select
    // repopulates detail, esc no longer closes)
    function hideEventDetail() {
        detail_panel.collapse();
    }
    function eventDetailCollapsed(){
        wipeEventDetail();
        grid.on('rowdblclick', toggleEventDetailContent);
        esckeymap.disable();
    };
    // Finally, add the detail panel (have to do it after function defs to hook
    // up the hide callback)
    detail_panel.add({
        xtype:'detailpanel',
        id: 'dpanelcontainer',
        onDetailHide: hideEventDetail
    });

    detail_panel.on('expand', function(ob, state) {
        toggleEventDetailContent();
    });

    detail_panel.on('collapse', function(ob, state) {
        eventDetailCollapsed();
    });
    // Hook up the "Last Updated" text
    var store = grid.getStore(),
        view = grid.getView();
    store.on('load', doLastUpdated);
    view.on('buffer', doLastUpdated);
    view.on('filterchange', function() {
        tbar.refreshmenu.setDisabled(!view.isValid());

        if ( !view.isValid() ) {
            var box = Ext.getCmp('lastupdated');
            box.setText(_t(''));
        }
    });

    // Detail pane should pop open when double-click on event
    grid.on("rowdblclick", toggleEventDetailContent);
    console_selection_model.on("rowselect", function(){
        if(detail_panel.isVisible()){
            toggleEventDetailContent();
        }
        });

    // When multiple events are selected, detail pane should blank
    console_selection_model.on('rangeselect', wipeEventDetail);

    // Key mapping for ESC to close detail pane
    var esckeymap = new Ext.KeyMap(document, {
        key: Ext.EventObject.ESC,
        fn: hideEventDetail
    });
    // Start disabled since pane is collapsed
    esckeymap.disable();

});
