[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
# scrapy-cluster
## Development:
1. Install dev packages:
```bash
pip install -r ./requirements-dev.txt
```
2. Install pre-commit hook
```bash
pre-commit install
```
## Testing
- Run:
```bash
pip install -r ./requirements-dev.txt
pytest
```



# Deployment

### 1. Prepare a new server on the provider side


### 2. Working with Ansible-playbook

##### a) install Ansible (if it’s not already installed), the installation instructions: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html

##### b) Create a key-pair or use an existing one and a public_key upload to a destination server(s) (/root/.ssh/authorized_keys in our case)

##### c) specify correct IPs in hosts.txt and specify correct path to SSH in group_vars/dev and group_vars/prod .key*pem. Check the correctness of the connection to the server (being in the ansible folder) with the command:
```bash
ansible dev -m ping
```
or
```bash
ansible prod -m ping
```
and get a result like:
```bash
ubuntu_dev | SUCCESS => {
    "ansible_facts": {
        "discovered_interpreter_python": "/usr/bin/python3"
    },
    "changed": false,
    "ping": "pong"
}
```
	d) run ansible-playbook:
```bash
ansible-playbook playbook.yml --limit dev
and
ansible-playbook playbook.yml --limit prod
```
and make sure there are no errors
```bash
ok=11   changed=9    unreachable=0    failed=0    skipped=0    rescued=0 ignored=0
```

If you use non-root user, the next section will need to be added to playbook.yaml
```bash
    - name: Add user to docker group
      user:
        name: "{{ansible_user}}"
        group: docker
```


### 3. Clone repo from Github to the destination server

##### a) You will need to generate and upload a new public key to Github or use an existing one by uploading it to the destination server to /root/.ssh/ folder (with 0600 permission) and then use the following command:
```bash
git clone git@github.com:Sellgo/scrapy-cluster.git --config core.sshCommand="ssh -i ~/location/to/private_ssh_key"
```

##### b) take a necessary actions (according to the google docs https://docs.google.com/document/d/1JklBlWHfwzO16MXee5RgyQXnQvTATW6E7XZFstFELm0)
```bash
vim .gitmodules
url = git@github.com:Sellgo/core

vim .git/config
url = git@github.com:Sellgo/core

git submodule update --remote or git submodule update --init --recursive
```

### 4. First build and SSL certificate installation

##### a) comment all lines concerning SSL in nginx_certbot/nginx-conf/default_dev.conf (nginx_certbot/nginx-conf/default_prod.conf), bringing it to the following  view:
```bash
server {
        listen 80;
        listen [::]:80;
        server_name scrapy-api.sellgo-dev.com scrapyd.sellgo-dev.com;

        location ~ /.well-known/acme-challenge {
          allow all;
          root /var/www/html;
        }

        location / {
                rewrite ^ https://$host$request_uri? permanent;
        }
}
```

##### b) create /var/www/html folder (it will be needed for nginx configuration)

##### c) create a directory in /root/ for Diffie-Hellman key and enerate the key with the openssl command:
```bash
mkdir /root/dhparam
sudo openssl dhparam -out /root/dhparam/dhparam-2048.pem 2048
```
	
##### d) correct docker-compose-dev.yml (docker-compose-prod.yml) in certbot-part:
```bash
    command: certonly --webroot --webroot-path=/var/www/html --email admin@sellgo-dev.com --agree-tos --staging --no-eff-email -d scrapy-api.sellgo-dev.com -d scrapyd.sellgo-dev.com
```
##### e) start deploying and launch containers:
```bash
docker-compose -f docker-compose-dev.yml up -d
or
docker-compose -f docker-compose-prod.yml up -d
```
(from this moment will describe the actions for DEV, but all the same should be working for PROD as well)

If everything was successful, your webserver service should be up and the certbot container will have exited with a 0 status message:
```bash
docker-compose -f docker-compose-dev.yml ps
  Name                 Command               State          Ports
------------------------------------------------------------------------
certbot     certbot certonly --webroot ...   Exit 0
webserver   nginx -g daemon off;             Up       0.0.0.0:80->80/tcp
```

You can now check that your credentials have been mounted to the webserver container:
```bash
docker-compose -f docker-compose-dev.yml exec webserver ls -la /etc/letsencrypt/live
total 16
drwx------    3 root     root          4096 Jul 30 15:14 .
drwxr-xr-x    9 root     root          4096 Jul 30 15:42 ..
-rw-r--r--    1 root     root           740 Jul 30 15:14 README
drwxr-xr-x    2 root     root          4096 Jul 30 15:42 your.domain.name
```

##### f) Edit the certbot service definition to remove the --staging flag. Open docker-compose-dev.yml and correct the command line:
```bash
command: certonly --webroot --webroot-path=/var/www/html --email admin@sellgo-dev.com --agree-tos --force-renew --no-eff-email d scrapy-api.sellgo-dev.com -d scrapyd.sellgo-dev.com
```

You can now run docker-compose up to recreate the certbot container and its relevant volumes. We will also include the --no-deps option to tell Compose that it can skip starting the webserver service, since it is already running:
```bash
docker-compose -f docker-compose-dev.yml up --force-recreate --no-deps certbot
```

##### g) Change nginx configuration
```bash
docker-compose -f docker-compose-dev.yml stop webserver
```
And bring /nginx_certbot/nginx_conf/defauld_dev.conf to the initial form (remove comments).
Once done — run the command:
```bash
docker-compose -f docker-compose-dev.yml up -d --force-recreate --no-deps webserver
```

##### h) Remove --force-renew key from certbot service (to avoid renewing every time when docker-compose restarting and exceeding Let’s Encrypt rate limit):
```bash
command: certonly --webroot --webroot-path=/var/www/html --email admin@sellgo-dev.com --agree-tos --no-eff-email d scrapy-api.sellgo-dev.com -d scrapyd.sellgo-dev.com
```

create /root/ssl_renew.sh (with permissions 777)
```bash
#!/bin/bash

COMPOSE="/usr/local/bin/docker-compose -f docker-compose-dev.yml --ansi never"

cd /root/scrapy-cluster
$COMPOSE run certbot renew && $COMPOSE kill -s SIGHUP webserver
```

and add the following cron for renewing certificates:
```bash
0 12 * * * /root/ssl_renew.sh >> /var/log/cron.log 2>&1
```


### 5. CircleCI

##### a) Set Up scrapy-cluster project in Projects menu

##### b) In Project Settings add Additional SSH Keys for PROD and DEV (generate new or, as a variant, can be used the existent keys for Ansible)

##### c) In Project Settings add Environment Variables add the following:
```bash
SSH_HOST_DEV
SSH_HOST_PROD
SSH_USER
```

##### d) Push changes in th repo and inspect pipeline
