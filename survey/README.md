# SERVER Config
In the following examples, it is assumed that your user name is `testuser` and this repository is located at the root of your home folder. 
- Copy/Downlad this folder to your home diretory. (This `README.md` file would be located at `/home/testuser/ultimatum/survey/README.md`)
- Install Required packages in `requirements.txt` are installed inside a python-environment folder `/home/testuser/ultimatum/env`)
    ```bash
    python -m venv env
    python source env/bin/activate
    pip install -r requirements.txt
    ```
- If not yet available, [install nginx](https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-open-source/)

- Follow the [installation and configuration of flask application with nginx+gunicorn](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04)


### Service configuration:
The following variables in the file `server_config/ultimatum.service` should be configured as follow:
- $USER: The user as which the application should be run
- $PATH_TO_WORKING_DIRECTORY: Abolute path pointing to the `code` folder. e.g. (`/home/testuser/ultimatum/code`)
- $PATH_TO_PYHTON_ENV: Abolute path to the env directory where the python packages have been installed. e.g. (`/home/testuser/ultimatum/env`s)
- $ADMIN_SECRET: A secret password that you will need to add job informations from the website
- $PATH_TO_GUNICORN: Abolute path to the `gunicorn` binary. e.g. (`/home/testuser/ultimatum/env/bin/gunicorn`)
- $PATH_TO_THE_SERVICE_SOCKET: Abolute path to the filename that will be used as socket for the service. e.g. (`/home/testuser/ultimatum/ultimatum.sock`)
Afterward,

### ultimatum.nginx
The following variables in the file `server_config/ultimatum.nginx` should be configured as follow:  
- $SERVER_NAME: The name of your server. (e.g. `ultimatum-experiment.com`)
- $PATH_TO_THE_SERVICE_SOCKET: Abolute path to the service socket. Should match the one defined in `server_config/ultimatum.service`
- $PATH_TO_STATIC_DIR: Abolute path to the static folder. e.g. (`/home/testuser/ultimatum/survey/static`)