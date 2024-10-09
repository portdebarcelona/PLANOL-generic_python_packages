// Variables a modificar segons projecte
def jenkinsToken = 'lalaguna-visorwab'
def dockerProject = 'lalaguna'
def dockerImage = 'visorwab'

pipeline {
  agent {
    label 'gisnordldwf1'
  }

  options {
    buildDiscarder(logRotator(numToKeepStr: '15'))
    disableConcurrentBuilds()
  }

  environment {
    // GitLab
    GITHUB_LAST_TAG = "${env.GITHUB_REF.split('/')[2]}"
    BRANCH_NAME = "${env.GITHUB_EVENT == 'push' ? env.BRANCH_NAME : sh(script: "git rev-list -n 1 ${GITHUB_LAST_TAG}", returnStdout: true).trim()}"

    // Docker (build image & push)
    /*
    DOCKER_REGISTRY = 'planolport'
    DOCKER_PROJECT = 'moute'
    DOCKER_IMAGE = 'web'
    DOCKER_IMAGE_URL = "${DOCKER_REGISTRY}/${DOCKER_PROJECT}/${DOCKER_IMAGE}"
    DOCKER_REGISTRY_CREDENTIALS = credentials('registry-pwd')
    DOCKER_DEV_TAG = 'dev'
    */
    // DEVPI
    DEVPI_ROOT_PASSWORD = credentials('devpi-root-password')

    // Docker deploy server (dev)
    DOCKER_DEPLOY_HOST_IP = '192.168.0.216'
    DOCKER_DEPLOY_CERTIFICATE = 'docker-srvdocker1-ssl'
    DOCKER_DEPLOY_SERVICE_NAME = 'moute-web_moute-web'
  }

  stages {
    // Stage A.
    stage('Checkout code') {
      steps {
        checkout([
          $class: 'GitSCM',
          branches: [[name: "${BRANCH_NAME}"]],
          changelog: false,
          doGenerateSubmoduleConfigurations: false,
          submoduleCfg: [],
          userRemoteConfigs: [
            [credentialsId: 'apb-admincicd-token', url: repo.url ]
          ],
          poll: false
        ])
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    // Stage B.
    stage('Initialize environment') {
      steps {
        script {
          sh "env"
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Build & Upload Oracle Spatial Package') {
      when {
        anyOf {
          changeset "cx_oracle_spatial_pckg/setup.py"
        }
      }
      agent {
        docker {
          reuseNode true
          image 'python:alpine3.19'
          args '-u root'
        }
      }
      steps {
        script {
          sh """
          pip install -r requirements.txt
          cd cx_oracle_spatial_pckg
          python setup.py bdist_wheel
          devpi use http://gisplanoldev.port.apb.es:3141
          devpi login root --password ${env.DEVPI_PASSWORD}
          devpi use http://gisplanoldev.port.apb.es:3141/root/web2py
          devpi upload \$(find . -name '*.whl')
          """
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }
  }
}
