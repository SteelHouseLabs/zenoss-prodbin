(function(){
    Ext.ns('Zenoss.VTypes');

    var ip_regex = new RegExp("(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)");
    var hex_regex = new RegExp("^#?([a-f]|[A-F]|[0-9]){3}(([a-f]|[A-F]|[0-9]){3,5})?$");
    var numcmp_regex = new RegExp("^(\>=|\<=|\>|\<|=)?\s*([0-9]+)$");
    var alpha_num_space = new RegExp(/[a-z_\s\d]/i);

    /**
     * These are the custom validators defined for
     * our zenoss forms. The xtype/vtype custom is to have the
     * name of the vtype all lower case with no word separator.
     *
     **/
    var vtypes = {
        /**
         * Allows int comparisons like 4,>2,<=5
         */
        numcmp: function(val, field) {
            return numcmp_regex.test(val);
        },
        numcmpText: _t('Enter a valid comparison (ex: 4, <2, >=1)'),

        /**
         * The number must be greater than zero. Designed for us in NumberFields
         **/
        positive: function(val, field) {
            return (val >= 0);
        },
        positiveText: _t('Must be greater than or equal to 0'),

        /**
         * Between 0 and 1 (for float types)
         **/
        betweenzeroandone: function(val, field) {
            return (val >= 0 && val <=1);
        },
        betweenzeroandoneText: _t('Must be between 0 and 1'),
        ipaddress: function(val, field) {
            return ip_regex.test(val);
        },
        ipaddressText: _t('Invalid IP address'),

        /**
         * Hex Number (for colors etc)
         **/
        hexnumber: function(val, field) {
            return hex_regex.test(val);
        },
        hexnumberText: _t('Must be a 6 or 8 digit hexadecimal value.'),

        /**
         * Modifies alpha number to allow spaces
         **/
        alphanumspace: function(val, field) {
            return alpha_num_space.test(val);
        },
        alphanumspaceText: _t('Must be an alphanumeric value or a space '),
        alphanumspaceMask: alpha_num_space
    };

    Ext.apply(Ext.form.VTypes, vtypes);
}());

