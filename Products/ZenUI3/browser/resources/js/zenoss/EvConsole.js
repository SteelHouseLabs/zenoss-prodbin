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

    // Get the container surrounding master/detail, for adding the toolbar
    var container = Ext.getCmp('center_panel_container');

    // Add a CSS class to scope some styles that affect other parts of the UI
    container.on('render', function(){container.el.addClass('zenui3');});

    var console_store = Ext.create('Zenoss.events.Store', { });

    // if the user has no global roles and does not have any admin. objects
    // do not show any events.
    if (!_has_global_roles() && _managed_objects().length == 0){
        console_store =  Ext.create('Zenoss.events.Store', {
        });
    }

    // Selection model
    var console_selection_model = Ext.create('Zenoss.EventPanelSelectionModel', {
        gridId: 'events_grid'
    });

    /*
     * THE GRID ITSELF!
     */

    var grid = Ext.create('Zenoss.events.Grid', {
        region: 'center',
        tbar: new Zenoss.EventConsoleTBar({
            region: 'north',
            gridId: 'events_grid',
            hideDisplayCombo: true,
            newwindowBtn: false
        }),
        appendGlob: true,
        defaultFilters: {
            severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
            eventState: [Zenoss.STATUS_NEW, Zenoss.STATUS_ACKNOWLEDGED],
            // _managed_objects is a global function sent from the server, see ZenUI3/security/security.py
            tags: _managed_objects()
        },
        id: 'events_grid',
        stateId: Zenoss.env.EVENTSGRID_STATEID,
        enableDragDrop: false,
        stateful: true,
        rowSelectorDepth: 5,
        store: console_store, // defined above
        // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
        // the resultFields associated with the context.
        columns: Zenoss.env.COLUMN_DEFINITIONS,
        displayTotal: false,
        // Map some other keys
        keys: [{
        // Enter to pop open the detail panel
            key: Ext.EventObject.ENTER,
            fn: toggleEventDetailContent
        }],
        selModel: console_selection_model, // defined above

        // no explicit toolbar at the bottom
        bbar: [

        ]
    });
    console_selection_model.grid = grid;
    // Add it to the layout
    master_panel.add(grid);
    Zenoss.util.callWhenReady('events_grid', function(){
        Ext.getCmp('events_grid').setContext(Zenoss.env.PARENT_CONTEXT);
    });
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
        var selections = console_selection_model.getSelection();
        if (selections.length) {
            showEventDetail(selections[0]);
        } else {
            wipeEventDetail();
        }
    }

    // Pop open the event detail pane and populate it with the appropriate data
    // and switch triggers (single select repopulates detail, esc to close)
    function showEventDetail(r) {
        Ext.getCmp('dpanelcontainer').load(r.data.evid);
        grid.un('itemdblclick', toggleEventDetailContent);

        detail_panel.expand();
        detail_panel.show();
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
        detail_panel.hide();
    }
    function eventDetailCollapsed(){
        wipeEventDetail();
        grid.on('itemdblclick', toggleEventDetailContent);
        esckeymap.disable();
    };
    // Finally, add the detail panel (have to do it after function defs to hook
    // up the hide callback)
    detail_panel.add({
        xtype:'detailpanel',
        id: 'dpanelcontainer',
        onDetailHide: hideEventDetail
    });
    // Make the detail panel collapsible
    detail_panel.animCollapse = false;
    // render so that the detail panel has html elements
    detail_panel.show();
    detail_panel.collapse();


    detail_panel.on('collapse', function(ob, state) {
        eventDetailCollapsed();
    });


    // Detail pane should pop open when double-click on event
    grid.on("itemdblclick", toggleEventDetailContent);
    console_selection_model.on("select", function(){
        if(!detail_panel.collapsed){
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
