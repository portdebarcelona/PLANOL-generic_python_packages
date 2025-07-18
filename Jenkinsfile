def jenkinsToken = 'planol-generic-python-packages'
def dockerProject = 'planolport'
def dockerBaseImage = 'gdal_oracle'
def dockerAllPackagesImage = 'python_gdal_oracle_geopandas'
def k8sDevCredentials = 'jenkins-gisplanoldev'
def k8sPreCredentials = 'jenkins-gisplanolpre'
def k8sProCredentials = 'jenkins-gisplanolpro'
def k8sNamespace = 'portbcn'
def k8sPodLabelApp = 'app=python-planol-python-packages-doc'
def ref = "${env.ref}"
def tagRelease = "${env.ref}"

echo "Checking if event is tag deleted..."
try {
  if (env.deleted == 'true') {
    echo "Tag deleted, aborting pipeline"
    currentBuild.result = 'ABORTED'
    error('Tag deleted, aborting pipeline')
    return
  }
} catch (Exception e) {
  currentBuild.result = 'ABORTED'
  error('Delete tag event detected, ABORTING!')
}

if (ref.contains("refs/tags")) {
    tagRelease = ref.replaceAll("refs/tags/", "")
    ref = "refs/tags/\\d+\\.\\d+\\.\\d+\$"
    if (env.ref.matches("refs/tags/\\d+\\.\\d+\\.\\d+.*")) {
        echo "Tag release detected: ${tagRelease}"
    } else {
        echo "Invalid tag format"
    }
}

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
    GITHUB_EVENT = "${env.X_GitHub_Event}"

    // Docker (build image & push)
    DOCKER_REGISTRY = 'registry-1.docker.io/v2'
    DOCKER_PROJECT = "${dockerProject}"
    DOCKER_BASE_IMAGE = "${dockerBaseImage}"
    DOCKER_ALL_PACKAGES_IMAGE = "${dockerAllPackagesImage}"
    DOCKER_BASE_URL = "${DOCKER_PROJECT}/${DOCKER_BASE_IMAGE}"
    DOCKER_ALL_PACKAGES_URL = "${DOCKER_PROJECT}/${DOCKER_ALL_PACKAGES_IMAGE}"
    DOCKER_REGISTRY_CREDENTIALS = 'dockerhub-registry-credentials'
    DOCKER_DEV_TAG = 'training'
    DOCKER_PRE_TAG = 'preprod'
    
    // Kubernetes deployment
    K8S_NAMESPACE = "${k8sNamespace}"
    K8S_DEV_CREDENTIALS = "${k8sDevCredentials}"
    K8S_PRE_CREDENTIALS = "${k8sPreCredentials}"
    K8S_PRO_CREDENTIALS = "${k8sProCredentials}"
    K8S_POD_LABEL_APP = "${k8sPodLabelApp}"
    K8S_DEV_HOST = "${env.K8S_DEV}"
    K8S_PRE_HOST = "${env.K8S_PRE}"
    K8S_PRO_HOST = "${env.K8S_PRO}"
  }

  triggers {
    GenericTrigger(
      token: "${jenkinsToken}",
      genericHeaderVariables: [
          [key: 'X-GitHub-Event', regexpFilter: '']
        ],
      genericVariables: [
          [expressionType: 'JSONPath', key: 'event_name', value: '$.event_name'],
          [expressionType: 'JSONPath', key: 'git_repo_url', value: '$.project.git_http_url'],
          [expressionType: 'JSONPath', key: 'project_id', value: '$.project.id'],
          [expressionType: 'JSONPath', key: 'project_name', value: '$.project.name'],
          [expressionType: 'JSONPath', key: 'project_namespace', value: '$.project.path_with_namespace'],
          [expressionType: 'JSONPath', key: 'user_name', value: '$.pusher.name'],
          [expressionType: 'JSONPath', key: 'checkout_sha', value: '$.checkout_sha'],
          [expressionType: 'JSONPath', key: 'message', value: '$.message', value: 'UNDEFINED'],
          [expressionType: 'JSONPath', key: 'total_commits_count', value: '$.total_commits_count'],
          [expressionType: 'JSONPath', key: 'ref', value: '$.ref', defaultValue: ''],
          [expressionType: 'JSONPath', key: 'deleted', value: '$.deleted']
        ],
      causeString: 'Triggered on "$ref" by "$user_name"',
      regexpFilterText: '$ref',
      regexpFilterExpression: "${ref}"
    )
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

    stage('Notify Pipeline Start') {
      steps {
        script {
          withCredentials([
            string(credentialsId: 'teams-webhook-dev', variable: 'TEAMS_WEBHOOK_DEV'),
            string(credentialsId: 'teams-webhook-pre', variable: 'TEAMS_WEBHOOK_PRE'),
            string(credentialsId: 'teams-webhook-pro', variable: 'TEAMS_WEBHOOK_PRO')
          ]) {
            def teamsWebhook = ''
            if (ref.contains("training")) {
              teamsWebhook = TEAMS_WEBHOOK_DEV
            } else if (ref.contains("preprod")) {
              teamsWebhook = TEAMS_WEBHOOK_PRE
            } else if (ref.contains("master")) {
              teamsWebhook = TEAMS_WEBHOOK_PRO
            }

            if (teamsWebhook) {
              office365ConnectorSend(
                webhookUrl: teamsWebhook,
                message: "Iniciando Pipeline para ref: ${ref}",
                status: 'STARTED'
              )
            } else {
              echo "No se definió Webhook para la rama/ref: ${ref}"
            }
          }
        }
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
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
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
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
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
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
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
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
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
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
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
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
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
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Docker build & push Dockerfile Base') {
      when {
        allOf {
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
          changeset "Dockerfile.base"
        }
      }
      steps {
        script {
          def tag = ''
          if (env.REPO_BRANCH == 'training') {
            tag = DOCKER_DEV_TAG
          } else if (env.REPO_BRANCH == 'preprod') {
            tag = DOCKER_PRE_TAG
          } else {
            error "Branch not recognized for Docker build."
          }
            docker.withRegistry("", "${DOCKER_REGISTRY_CREDENTIALS}") {
            image = docker.build("${DOCKER_BASE_URL}", "--no-cache -f Dockerfile.base .")
            image.push(tag)
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Docker build & push Dockerfile with all packages') {
      when {
        anyOf {
          expression { env.REPO_BRANCH == 'training' || env.REPO_BRANCH == 'preprod' }
        }
      }
      steps {
        script {
          def tag = ''
          if (env.REPO_BRANCH == 'training') {
            tag = DOCKER_DEV_TAG
          } else if (env.REPO_BRANCH == 'preprod') {
            tag = DOCKER_PRE_TAG
          } else {
            error "Branch not recognized for Docker build."
          }
            docker.withRegistry("", "${DOCKER_REGISTRY_CREDENTIALS}") {
            image = docker.build("${DOCKER_ALL_PACKAGES_URL}", "--build-arg ARG_DOCKER_TAG=${tag} --no-cache -f Dockerfile .")
            image.push(tag)
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Kubernetes restart python packages doc pod DEV') {
      when {
        anyOf {
            expression { env.REPO_BRANCH == 'training' }
        }
      }
      steps {
        script {
          withKubeConfig([credentialsId: "${K8S_DEV_CREDENTIALS}", serverUrl: "${K8S_DEV_HOST}"]) {
            sh '''
              kubectl delete po -l ${K8S_POD_LABEL_APP} --force --grace-period=0 -A
              kubectl get po -l ${K8S_POD_LABEL_APP} -A
            '''
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Kubernetes restart python packages doc pod PRE') {
      when {
        anyOf {
            expression { env.REPO_BRANCH == 'preprod' }
        }
      }
      steps {
        script {
          withKubeConfig([credentialsId: "${K8S_PRE_CREDENTIALS}", serverUrl: "${K8S_PRE_HOST}"]) {
            sh '''
              kubectl delete po -l ${K8S_POD_LABEL_APP} --force --grace-period=0 -A
              kubectl get po -l ${K8S_POD_LABEL_APP} -A
            '''
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Docker build & push (TAG RELEASE)') {
      when {
        expression { env.ref.matches("refs/tags/\\d+\\.\\d+\\.\\d+.*") }
        expression { env.REPO_BRANCH == 'master' }
      }
      steps {
        script {
            TAG_RELEASE = env.ref.replaceFirst("refs/tags/", "")
            echo "Tag detected: ${TAG_RELEASE}"

            docker.withRegistry("", "${DOCKER_REGISTRY_CREDENTIALS}") {
            image = docker.build("${DOCKER_BASE_URL}", "--no-cache -f Dockerfile.base .")
            image.push("${TAG_RELEASE}")
            image.push("latest")
            image = docker.build("${DOCKER_ALL_PACKAGES_URL}", "--build-arg ARG_DOCKER_TAG=latest --no-cache -f Dockerfile .")
            image.push("${TAG_RELEASE}")
            image.push("latest")
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }

    stage('Kubernetes restart python packages doc pod PRO') {
      when {
        expression { env.ref.matches("refs/tags/\\d+\\.\\d+\\.\\d+.*") }
        expression { env.REPO_BRANCH == 'master' }
      }
      steps {
        script {
          withKubeConfig([credentialsId: "${K8S_PRO_CREDENTIALS}", serverUrl: "${K8S_PRO_HOST}"]) {
            sh '''
              kubectl delete po -l ${K8S_POD_LABEL_APP} --force --grace-period=0 -A
              kubectl get po -l ${K8S_POD_LABEL_APP} -A
            '''
          }
        }
      }
      post {
        success { echo 'success' }
        failure { echo 'failed' }
      }
    }
  }
  post {
    always {
      script {
        withCredentials([
          string(credentialsId: 'teams-webhook-dev', variable: 'TEAMS_WEBHOOK_DEV'),
          string(credentialsId: 'teams-webhook-pre', variable: 'TEAMS_WEBHOOK_PRE'),
          string(credentialsId: 'teams-webhook-pro', variable: 'TEAMS_WEBHOOK_PRO')
        ]) {
          def teamsWebhook = ''
          if (ref.contains("training")) {
            teamsWebhook = TEAMS_WEBHOOK_DEV
          } else if (ref.contains("preprod")) {
            teamsWebhook = TEAMS_WEBHOOK_PRE
          } else if (ref.contains("master")) {
            teamsWebhook = TEAMS_WEBHOOK_PRO
          }

          def buildStatus = currentBuild.result ?: 'SUCCESS'

          if (teamsWebhook) {
            office365ConnectorSend(
              webhookUrl: teamsWebhook,
              message: "Pipeline finalizado con estado: ${buildStatus} en ref: ${ref}",
              status: buildStatus
            )
          } else {
            echo "No se definió Webhook para la rama/ref: ${ref}"
          }
        }
        cleanWs()
      }
    }
  }
}