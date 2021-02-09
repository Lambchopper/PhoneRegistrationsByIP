Phone Registrations by IP
Created by D. Lamb

This tool was created to solve a problem where Cisco Mobile Remote Access phones would occasionally
fail over to our backup Expressway pair due to residential network issues outside of our control.

This tool will use the RIS service to find any Phones that are registered with a specific IP (in
our case the EXP-C of our Co-Lo deployment).  It compiles a list of these phones and then emails
the list and restarts the phones to force them to re-register.

This script is scheduled using MS Task scheduler (but cron should work too if you have a *nix
environment). We runit at 5 AM to fail these phones back and the email notifies our help desk in case
the restart introduces an issue for an end user.

To use this script, you will need to configure the variables at the op for your specific needs.

The script requires the following Python Modules:
zeep 	- SOAP Client for interacting with UCM's RIS service
urllib3 - To handle the SSL connection and diasble warnings if you are not using CA signed Certs
smtplib	- Email functionality
