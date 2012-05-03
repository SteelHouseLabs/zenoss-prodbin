(function(){
    /**
     * This file contains overrides we are appyling to the Ext framework. These are default values we are setting
     * and convenience methods on the main Ext classes.
     **/


    /**
     * We had previously used the bool passed into disable to
     * toggle the disabledness of the button.
     **/
    Ext.button.Button.override({
        disable: function(bool) {
            if (bool || !Ext.isDefined(bool)) {
                this.callOverridden();
            } else {
                this.enable();
            }
        }
    });

    /**
     * This makes the default value for checkboxes getSubmitValue (called by getFieldValues on the form)
     * return true/false if it is checked or unchecked. The normal default is "on" or nothing which means the
     * key isn't even sent to the server.
     **/
    Ext.override(Ext.form.field.Checkbox, {
        inputValue: true,
        uncheckedValue: false
    });

    /**
    * Splitter needs to be resized thinner based on the older UI. The default is 5
    **/
   Ext.override(Ext.resizer.Splitter, {
       width: 2
   });

    /**
     * In every one of our panels we want border and frame to be false so override it on the base class.
     **/
    Ext.override(Ext.panel.Panel, {
        frame: false,
        border: false
    });

    /**
     * Refs were removed when going from Ext3 to 4, we rely heavily on this feature and it is much more
     * concise way of accessing children so we are patching it back in.
     **/
    Ext.override(Ext.AbstractComponent, {
        initRef: function() {
            if(this.ref && !this.refOwner){
                var levels = this.ref.split('/'),
                last = levels.length,
                i = 0,
                t = this;
                while(t && i < last){
                    t = t.ownerCt;
                    ++i;
                }
                if(t){
                    t[this.refName = levels[--i]] = this;
                    this.refOwner = t;
                }
            }
        },
        recursiveInitRef: function() {
            this.initRef();
            if (Ext.isDefined(this.items)) {
                Ext.each(this.items.items, function(item){
                    item.recursiveInitRef();
                }, this);
            }
            if (Ext.isFunction(this.child)) {
                var tbar = this.child('*[dock="top"]');
                if (tbar) {
                    tbar.recursiveInitRef();
                }
                var bbar = this.child('*[dock="bottom"]');
                if (bbar) {
                    bbar.recursiveInitRef();
                }
            }
        },
        removeRef: function() {
            if (this.refOwner && this.refName) {
                delete this.refOwner[this.refName];
                delete this.refOwner;
            }
        },
        onAdded: function(container, pos) {
            this.ownerCt = container;
            this.recursiveInitRef();
            this.fireEvent('added', this, container, pos);
        },
        onRemoved: function() {
            this.removeRef();
            var me = this;
            me.fireEvent('removed', me, me.ownerCt);
            delete me.ownerCt;
        }
    });


    /**
     * Back compat for Ext3 Component grid definitions.
     * NOTE: This only works if you follow the convention of having the xtype be the same
     * as the last part of the namespace defitions. (e.g. "Zenoss.component.foo" having an xtype "foo")
     * @param xtype
     * @param cls
     */
    Ext.reg = function(xtype, cls){
        if (Ext.isString(cls)) {
            Ext.ClassManager.setAlias(cls, 'widget.'+xtype);
        } else {
            // try to register the component
            var clsName ="Zenoss.component." + xtype;
            if (Ext.ClassManager.get(clsName)) {
                Ext.ClassManager.setAlias(clsName, 'widget.'+xtype);
            }else {
                throw Ext.String.format("Unable to to register the xtype {0}: change the Ext.reg definition from the object to a string", xtype);
            }
        }
    };

    /**
     * The Ext.grid.Panel component row selection has a flaw in it:

     Steps to recreate:
     1. Create a standard Ext.grid.Panel with multiple records in it and turn "multiSelect: true"
     Note that you can just go to the documentation page
     http://docs.sencha.com/ext-js/4-0/#!/api/Ext.grid.Panel and insert the multiSelect:
     true line right into there and flip to live preview.

     2. Select the top row, then press and hold shift and click on the second row, then the third row,
     then the fourth. You would expect to see all 4 rows selected but instead you just get the last two.

     3. For reference, release the shift and select the bottom row (4th row). Now press and hold shift
     and select the 3rd row, then the 2nd row, then the 1st row. You now see all four rows selected.

     To Fix this I have to override the Ext.selection.Model to handle the top down versus bottom up selection.
     *
     */
    Ext.override(Ext.selection.Model, {
        /**
         * Selects a range of rows if the selection model {@link #isLocked is not locked}.
         * All rows in between startRow and endRow are also selected.
         * @param {Ext.data.Model/Number} startRow The record or index of the first row in the range
         * @param {Ext.data.Model/Number} endRow The record or index of the last row in the range
         * @param {Boolean} keepExisting (optional) True to retain existing selections
         */
        selectRange : function(startRow, endRow, keepExisting, dir){
            var me = this,
                store = me.store,
                selectedCount = 0,
                i,
                tmp,
                dontDeselect,
                records = [];

            if (me.isLocked()){
                return;
            }

            if (!keepExisting) {
                me.deselectAll(true);
            }

            if (!Ext.isNumber(startRow)) {
                startRow = store.indexOf(startRow);
            }
            if (!Ext.isNumber(endRow)) {
                endRow = store.indexOf(endRow);
            }

            // WG: create a flag to see if we are swapping
            var swapped = false;
            // ---

            // swap values
            if (startRow > endRow){
                // WG:  set value to true for my flag
                swapped = true;
                // ----
                tmp = endRow;
                endRow = startRow;
                startRow = tmp;
            }

            for (i = startRow; i <= endRow; i++) {
                if (me.isSelected(store.getAt(i))) {
                    selectedCount++;
                }
            }

            if (!dir) {
                dontDeselect = -1;
            } else {
                dontDeselect = (dir == 'up') ? startRow : endRow;
            }

            for (i = startRow; i <= endRow; i++){
                if (selectedCount == (endRow - startRow + 1)) {
                    if (i != dontDeselect) {
                        me.doDeselect(i, true);
                    }
                } else {
                    records.push(store.getAt(i));
                }
            }

            //WG:  START  CHANGE
            // This is my fix, we need to flip the order
            // for it to correctly track what was selected first.
            if(!swapped){
                records.reverse();
            }
            //WG:  END CHANGE



            me.doMultiSelect(records, true);
        }
    });

    /**
     * This is a workaround to make sure the node isn't null as it has happened
     * to be on occasion. These only affect the UI class switches.
     * See Trac Ticket #29912
     **/
    Ext.override(Ext.view.AbstractView, {
        // invoked by the selection model to maintain visual UI cues
        onItemDeselect: function(record) {
            var node = this.getNode(record);
            if(node) Ext.fly(node).removeCls(this.selectedItemCls);
        },
        // invoked by the selection model to maintain visual UI cues
        onItemSelect: function(record) {
            var node = this.getNode(record);
            if(node) Ext.fly(node).addCls(this.selectedItemCls);
        }
    });

    /*
    * This is a fix to a bug in Ext. When the scrollbar height is determined,
    * it takes into account the toolbar, column headers and filter row, for
    * lord knows what reason. This overrides in order to use the height of the
    * grid /body/ instead of the entire grid. The function is copied except one
    * line
    */
    Ext.override(Ext.panel.Table, {
       determineScrollbars: function() {
           var me = this,
               box,
               tableEl,
               scrollWidth,
               clientWidth,
               scrollHeight,
               clientHeight,
               verticalScroller = me.verticalScroller,
               horizontalScroller = me.horizontalScroller,
               curScrollbars = (verticalScroller   && verticalScroller.ownerCt === me ? 1 : 0) |
                               (horizontalScroller && horizontalScroller.ownerCt === me ? 2 : 0),
               reqScrollbars = 0; // 1 = vertical, 2 = horizontal, 3 = both

           // If we are not collapsed, and the view has been rendered AND filled, then we can determine scrollbars
           if (!me.collapsed && me.view && me.view.el && me.view.el.dom.firstChild && !me.changingScrollBars) {

               // Calculate maximum, *scrollbarless* space which the view has available.
               // It will be the Fit Layout's calculated size, plus the widths of any currently shown scrollbars

               /********************************
               *
               * BEGIN ZENOSS CHANGE
               *
               *********************************/
               // box = me.getSize();
               box = me.view.getSize();
               /********************************
               *
               * END ZENOSS CHANGE
               *
               *********************************/


               clientWidth  = box.width  + ((curScrollbars & 1) ? verticalScroller.width : 0);
               clientHeight = box.height + ((curScrollbars & 2) ? horizontalScroller.height : 0);

               // Calculate the width of the scrolling block
               // There will never be a horizontal scrollbar if all columns are flexed.

               scrollWidth = (me.headerCt.query('[flex]').length && !me.headerCt.layout.tooNarrow) ? 0 : me.headerCt.getFullWidth();

               // Calculate the height of the scrolling block
               if (verticalScroller && verticalScroller.el) {
                   scrollHeight = verticalScroller.getSizeCalculation().height;
               } else {
                   tableEl = me.view.el.child('table', true);
                   scrollHeight = tableEl ? tableEl.offsetHeight : 0;
               }

               // View is too high.
               // Definitely need a vertical scrollbar
               if (scrollHeight > clientHeight) {
                   reqScrollbars = 1;

                   // But if scrollable block width goes into the zone required by the vertical scrollbar, we'll also need a horizontal
                   if (horizontalScroller && ((clientWidth - scrollWidth) < verticalScroller.width)) {
                       reqScrollbars = 3;
                   }
               }

               // View height fits. But we stil may need a horizontal scrollbar, and this might necessitate a vertical one.
               else {
                   // View is too wide.
                   // Definitely need a horizontal scrollbar
                   if (scrollWidth > clientWidth) {
                       reqScrollbars = 2;

                       // But if scrollable block height goes into the zone required by the horizontal scrollbar, we'll also need a vertical
                       if (verticalScroller && ((clientHeight - scrollHeight) < horizontalScroller.height)) {
                           reqScrollbars = 3;
                       }
                   }
               }

               // If scrollbar requirements have changed, change 'em...
               if (reqScrollbars !== curScrollbars) {

                   // Suspend component layout while we add/remove the docked scrollers
                   me.suspendLayout = true;
                   if (reqScrollbars & 1) {
                       me.showVerticalScroller();
                   } else {
                       me.hideVerticalScroller();
                   }
                   if (reqScrollbars & 2) {
                       me.showHorizontalScroller();
                   } else {
                       me.hideHorizontalScroller();
                   }
                   me.suspendLayout = false;
               }
               // Lay out the Component.
               // Set a flag so that afterComponentLayout does not recurse back into here.
               me.changingScrollBars = true;
               me.doComponentLayout();
               me.changingScrollBars = false;
           }
       }
    });

    /**
     * This is a workaround to make scrolling smoother
     **/
 
    Ext.override(Ext.grid.PagingScroller, {
        // The default fetch percent is 35% this is a little too early for a smooth scrolling experience
       percentageFromEdge: 0.15
   }); 
   
   /**
    * workaround for scrollbars missing in IE. IE ignores the parent size between parent and child
    * so we end up with the part that should have scrollbars the same size as the child, thus
    * no scrollbars. This normalizes the sizes between elements in IE only.
    **/
   Ext.override(Ext.form.ComboBox, {
    onExpand: function() {
        var me = this,
            picker = this.getPicker();

        if(Ext.isIE){
            var parent, child = Ext.DomQuery.selectNode('#'+picker.id+' .list-ct'); 
            Ext.defer(function(){ // defer a bit so the grandpaw will have a height 
                    grandpaw = Ext.DomQuery.selectNode('#'+picker.id);
                    child.style.cssText = 'width:'+me.width+'px; height:'+grandpaw.style.height+';overflow:auto;';
                }, 100, me);
        }
        
    }   
   });
    
    
}());
