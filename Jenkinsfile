pipeline {
  agent any

  stages {
    stage('Print Build Info') {
      steps {
        echo "Build ID: ${env.BUILD_ID}"
        echo "Build Number: ${env.BUILD_NUMBER}"
      }
    }
  }
}
