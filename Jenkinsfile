pipeline {
  agent {
    label 'dockerproapb'
  }

  options {
    buildDiscarder(logRotator(numToKeepStr: '15'))
    disableConcurrentBuilds()
  }

  environment {
    // DEVPI
    //DEVPI_ROOT_PASSWORD = credentials('testpypi_api_token')
    // TESTPYPI
    TESTPYPI_API_TOKEN = credentials('testpypi-api-token')
  }

  stages {
    // Stage A.
    stage('Checkout code') {
      steps {
        checkout([
          $class: 'GitSCM',
          branches: [[name: "${GIT_BRANCH}"]],
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
      when {
        anyOf {
          changeset "cx_oracle_spatial_pckg/**"
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
          TWINE_USERNAME=__token__
          TWINE_PASSWORD=${env.TESTPYPI_API_TOKEN}
          python -m build
          twine upload --username __token__ --password ${env.TESTPYPI_API_TOKEN} --non-interactive -r testpypi dist/*
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