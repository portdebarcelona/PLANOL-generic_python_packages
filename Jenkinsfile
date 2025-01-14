pipeline {
  agent {
    label 'dockerproapb'
  }

  options {
    buildDiscarder(logRotator(numToKeepStr: '15'))
    disableConcurrentBuilds()
  }

  environment {
    TESTPYPI_API_TOKEN = credentials('testpypi-api-token')
    PYPI_API_TOKEN = credentials('pypi-api-token')
    REPO_BRANCH = "${GIT_BRANCH.split('/')[GIT_BRANCH.split('/').length - 1]}"
  }

  stages {
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

    stage('Build & Upload Package apb_extra_utils') {
      when {
        allOf {
          changeset "apb_extra_utils_pckg/**"
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
        }
      }
      agent {
        docker {
          reuseNode true
          image 'python:3.10-alpine'
          args '-u root'
        }
      }
      steps {
        script {
          if (env.REPO_BRANCH == 'training') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_extra_utils_pckg ${env.TESTPYPI_API_TOKEN} testpypi
            """
          } else if (env.REPO_BRANCH == 'preprod') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_extra_utils_pckg ${env.PYPI_API_TOKEN} pypi
            """
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Build & Upload Package apb_spatial_utils') {
      when {
        allOf {
          changeset "apb_spatial_utils_pckg/**"
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
        }
      }
      agent {
        docker {
          reuseNode true
          image 'python:3.10-alpine'
          args '-u root'
        }
      }
      steps {
        script {
          if (env.REPO_BRANCH == 'training') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_spatial_utils_pckg ${env.TESTPYPI_API_TOKEN} testpypi
            """
          } else if (env.REPO_BRANCH == 'preprod') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_spatial_utils_pckg ${env.PYPI_API_TOKEN} pypi
            """
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Build & Upload Package apb_extra_osgeo_utils') {
      when {
        allOf {
          changeset "apb_extra_osgeo_utils_pckg/**"
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
        }
      }
      agent {
        docker {
          reuseNode true
          image 'python:3.10-alpine'
          args '-u root'
        }
      }
      steps {
        script {
          if (env.REPO_BRANCH == 'training') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_extra_osgeo_utils_pckg ${env.TESTPYPI_API_TOKEN} testpypi
            """
          } else if (env.REPO_BRANCH == 'preprod') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_extra_osgeo_utils_pckg ${env.PYPI_API_TOKEN} pypi
            """
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Build & Upload Package apb_cx_oracle_spatial') {
      when {
        allOf {
          changeset "apb_cx_oracle_spatial_pckg/**"
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
        }
      }
      agent {
        docker {
          reuseNode true
          image 'python:3.10-alpine'
          args '-u root'
        }
      }
      steps {
        script {
          if (env.REPO_BRANCH == 'training') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_cx_oracle_spatial_pckg ${env.TESTPYPI_API_TOKEN} testpypi
            """
          } else if (env.REPO_BRANCH == 'preprod') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_cx_oracle_spatial_pckg ${env.PYPI_API_TOKEN} pypi
            """
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Build & Upload Package apb_pandas_utils') {
      when {
        allOf {
          changeset "apb_pandas_utils_pckg/**"
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
        }
      }
      agent {
        docker {
          reuseNode true
          image 'python:3.10-alpine'
          args '-u root'
        }
      }
      steps {
        script {
          if (env.REPO_BRANCH == 'training') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_pandas_utils_pckg ${env.TESTPYPI_API_TOKEN} testpypi
            """
          } else if (env.REPO_BRANCH == 'preprod') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_pandas_utils_pckg ${env.PYPI_API_TOKEN} pypi
            """
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Build & Upload Package apb_duckdb_utils') {
      when {
        allOf {
          changeset "apb_duckdb_utils_pckg/**"
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
        }
      }
      agent {
        docker {
          reuseNode true
          image 'python:3.10-alpine'
          args '-u root'
        }
      }
      steps {
        script {
          if (env.REPO_BRANCH == 'training') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_duckdb_utils_pckg ${env.TESTPYPI_API_TOKEN} testpypi
            """
          } else if (env.REPO_BRANCH == 'preprod') {
            sh """
              chmod +x build_pckg.sh
              ./build_pckg.sh apb_duckdb_utils_pckg ${env.PYPI_API_TOKEN} pypi
            """
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }
  }
}