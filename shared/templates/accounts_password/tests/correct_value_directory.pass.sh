#!/bin/bash
# This test only applies to platforms that check the pwquality.conf.d directory
# platform = Oracle Linux 8
# variables = var_password_pam_{{{ VARIABLE }}}={{{ TEST_VAR_VALUE }}}

# This test will ensure that OVAL also checks the configuration in 
# /etc/security/pwquality.conf.d/*.conf files

truncate -s 0 /etc/security/pwquality.conf

echo "{{{ VARIABLE }}} = {{{ TEST_CORRECT_VALUE }}}" \
>> /etc/security/pwquality.conf.d/test_file.conf
