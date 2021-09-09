Macbee
======

# SSH

If you do not have a key, generate it:

`$ sudo ssh-keygen-t rsa -b 4096 -C "your_email@domain.com"`

Copy it:

`$ ssh-copy-id remote_username@server_ip_address`

Test it:

`$ ssh remote_username@server_ip_address`
