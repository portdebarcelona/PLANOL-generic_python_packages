pipeline {
  agent {
    label 'NodoJenkins'
  }

  options {
    buildDiscarder(logRotator(numToKeepStr: '15'))
    disableConcurrentBuilds()
  }

  environment {
    // DEVPI
    DEVPI_ROOT_PASSWORD = credentials('devpi-root-password')
  }

  stages {
    // Stage A.
    stage('Checkout code') {
      steps {
        checkout([
          $class: 'GitSCM',
          branches: [[name: "*/training"]],
          extensions: [[$class: 'CloneOption', shallow: true, timeout: 360]],
          changelog: false,
          doGenerateSubmoduleConfigurations: false,
          submoduleCfg: [],
          userRemoteConfigs: [
            [credentialsId: 'apb-admincicd-token', url: "${GIT_URL}" ]
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
      /*
      when {
        anyOf {
          changeset "cx_oracle_spatial_pckg/setup.py"
        }
      }
      */
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
          ls -la
          pip install -r requirements.txt
          cd cx_oracle_spatial_pckg
          python setup.py bdist_wheel
          devpi use http://gisplanoldev.port.apb.es:3141
          devpi login root --password ${env.DEVPI_ROOT_PASSWORD}
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