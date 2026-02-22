## Email Harvester Script
A simple email harvester script using Duck Duck Go search engine.
This returns a few basic emails and the real benefit is to simply see how an organization structures their email addresses (john.smith@domain.com or jsmith@domain.com, etc).
The script prints to screen and dumps emails into a text file that is named using [domain_time].txt structure in the same directory as the script or into a directory specified as an optional argument.

### Usage
For a single domain and have the output saved in the same directory as the script:
```
./email_harvester.py example.com
```
You can also specify a directory to save the output file to:
```
./email_harvester.py example.com ~/tool/output
```
If you have a text file containing a list of domains, 1 per line and also want to specify the output file directory:
```
./email_harvester.py ~/path/to/file/domains.txt /home/user/tool/output
```
If output directory is not supplied then all output files will be saved to the same directory where the script is.
