pipeline {
    agent any
    
    environment {
        // Docker Configuration
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_REPO = 'tringuyen180303'
        IMAGE_NAME = 'rag-api'
        
        // Kubernetes Configuration
        K8S_NAMESPACE = 'rag-services'
        KUBECONFIG_CREDENTIAL_ID = 'kubeconfig'
        
        // Build Configuration
        BUILD_VERSION = "${env.BUILD_NUMBER}-${env.GIT_COMMIT.take(8)}"
        IMAGE_TAG = "${env.BRANCH_NAME == 'main' ? 'latest' : env.BRANCH_NAME}-${BUILD_VERSION}"
        
        // Credentials
        DOCKER_CREDENTIALS = credentials('docker-hub-credentials')
        LANGFUSE_CREDENTIALS = credentials('langfuse-keys')
        
        // Application Settings
        CHROMA_HOST = 'chroma.rag-services.svc.cluster.local'
        CHROMA_PORT = '8000'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        skipDefaultCheckout(false)
    }
    
    stages {
        stage('🔍 Setup & Validation') {
            steps {
                script {
                    echo "🚀 Starting RAG API CI/CD Pipeline"
                    echo "=================================="
                    echo "Build ID: ${env.BUILD_ID}"
                    echo "Build Number: ${env.BUILD_NUMBER}"
                    echo "Branch: ${env.BRANCH_NAME}"
                    echo "Git Commit: ${env.GIT_COMMIT}"
                    echo "Image Tag: ${IMAGE_TAG}"
                    echo "Environment: ${env.BRANCH_NAME == 'main' ? 'PRODUCTION' : 'DEVELOPMENT'}"
                    
                    // Validate required files
                    def requiredFiles = [
                        'app/api.py',
                        'app/settings.py',
                        'requirements.txt',
                        'Dockerfile',
                        'deployments/rag-services/fast_api.yaml'
                    ]
                    
                    requiredFiles.each { file ->
                        if (!fileExists(file)) {
                            error("❌ Required file missing: ${file}")
                        } else {
                            echo "✅ Found: ${file}"
                        }
                    }
                }
            }
        }
        
        stage('🧪 Code Quality & Testing') {
            parallel {
                stage('Lint & Format Check') {
                    steps {
                        script {
                            echo "🔍 Running code quality checks..."
                            sh '''
                                python3 -m venv venv
                                . venv/bin/activate
                                pip install --upgrade pip
                                pip install flake8 black isort safety bandit
                                
                                # Code formatting check
                                echo "Checking code formatting..."
                                black --check --diff app/ || echo "Code formatting issues found"
                                
                                # Import sorting check
                                echo "Checking import sorting..."
                                isort --check-only --diff app/ || echo "Import sorting issues found"
                                
                                # Linting
                                echo "Running flake8 linting..."
                                flake8 app/ --max-line-length=100 --ignore=E203,W503 || echo "Linting issues found"
                                
                                # Security check
                                echo "Running security scan..."
                                bandit -r app/ -f json -o bandit-report.json || echo "Security issues found"
                                safety check --json --output safety-report.json || echo "Dependency vulnerabilities found"
                            '''
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: '*-report.json', allowEmptyArchive: true
                        }
                    }
                }
                
                stage('Unit Tests') {
                    steps {
                        script {
                            echo "🧪 Running unit tests..."
                            sh '''
                                . venv/bin/activate
                                pip install pytest pytest-cov pytest-asyncio httpx
                                pip install -r requirements.txt
                                
                                # Run tests with coverage
                                python -m pytest tests/ -v --cov=app --cov-report=xml --cov-report=html --junitxml=test-results.xml || echo "Some tests failed"
                            '''
                        }
                    }
                    post {
                        always {
                            publishTestResults testResultsPattern: 'test-results.xml'
                            publishCoverage adapters: [
                                coberturaAdapter('coverage.xml')
                            ], sourceFileResolver: sourceFiles('STORE_LAST_BUILD')
                            archiveArtifacts artifacts: 'htmlcov/**', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        
        
        stage('🔧 Integration Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    echo "🔧 Running integration tests..."
                    sh '''
                        # Start test environment
                        if [ -f docker-compose.test.yml ]; then
                            docker-compose -f docker-compose.test.yml up -d
                            
                            # Wait for services
                            sleep 30
                            
                            # Run integration tests
                            . venv/bin/activate
                            python -m pytest tests/integration/ -v || echo "Integration tests failed"
                            
                            # Cleanup
                            docker-compose -f docker-compose.test.yml down
                        else
                            echo "No docker-compose.test.yml found, skipping integration tests"
                        fi
                    '''
                }
            }
        }
        
        stage('🚀 Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                script {
                    echo "🚀 Deploying to Staging environment..."
                    
                    withKubeConfig([credentialsId: 'kubeconfig']) {
                        sh '''
                            # Update deployment image
                            kubectl set image deployment/rag-api rag-api=${DOCKER_REGISTRY}/${DOCKER_REPO}/${IMAGE_NAME}:${IMAGE_TAG} -n ${K8S_NAMESPACE}-staging
                            
                            # Wait for rollout
                            kubectl rollout status deployment/rag-api -n ${K8S_NAMESPACE}-staging --timeout=300s
                            
                            # Verify deployment
                            kubectl get pods -n ${K8S_NAMESPACE}-staging -l app=rag-api
                        '''
                    }
                }
            }
        }
        
        stage('🧪 Staging Smoke Tests') {
            when {
                branch 'develop'
            }
            steps {
                script {
                    echo "🧪 Running smoke tests on staging..."
                    
                    sh '''
                        # Get staging endpoint
                        STAGING_ENDPOINT="http://rag-staging.example.com"  # Update with your staging URL
                        
                        # Run smoke tests
                        . venv/bin/activate
                        python tests/smoke/test_smoke.py --url=${STAGING_ENDPOINT} --environment=staging
                    '''
                }
            }
        }
        
        stage('🚀 Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo "🚀 Deploying to Production environment..."
                    
                    // Production deployment with manual approval
                    timeout(time: 10, unit: 'MINUTES') {
                        input message: 'Deploy to Production?', ok: 'Deploy',
                              submitterParameter: 'APPROVER',
                              parameters: [choice(name: 'DEPLOYMENT_TYPE', choices: 'rolling\nblue-green', description: 'Choose deployment strategy')]
                    }
                    
                    withKubeConfig([credentialsId: 'kubeconfig']) {
                        sh '''
                            # Update production deployment
                            kubectl set image deployment/rag-api rag-api=${DOCKER_REGISTRY}/${DOCKER_REPO}/${IMAGE_NAME}:${IMAGE_TAG} -n ${K8S_NAMESPACE}
                            
                            # Wait for rollout
                            kubectl rollout status deployment/rag-api -n ${K8S_NAMESPACE} --timeout=600s
                            
                            # Verify deployment
                            kubectl get pods -n ${K8S_NAMESPACE} -l app=rag-api
                            
                            # Update configmap if needed
                            kubectl patch configmap rag-config -n ${K8S_NAMESPACE} --patch '{"data":{"BUILD_VERSION":"'${BUILD_VERSION}'","DEPLOYED_BY":"'${APPROVER}'","DEPLOYED_AT":"'$(date -u +'%Y-%m-%dT%H:%M:%SZ')'"}}'
                        '''
                    }
                }
            }
        }
        
        stage('🧪 Production Smoke Tests') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo "🧪 Running production smoke tests..."
                    
                    sh '''
                        # Get production endpoint
                        PROD_ENDPOINT="https://rag-api.example.com"  # Update with your production URL
                        
                        # Run smoke tests
                        . venv/bin/activate
                        python tests/smoke/test_smoke.py --url=${PROD_ENDPOINT} --environment=production
                        
                    '''
                }
            }
        }
        
      
    
    post {
        always {
            script {
                echo "🧹 Cleaning up..."
                
                // Clean up Docker images
                sh '''
                    docker image prune -f --filter="label!=keep"
                    docker system prune -f
                '''
                
                // Clean up virtual environment
                sh 'rm -rf venv'
                
                // Archive important artifacts
                archiveArtifacts artifacts: 'logs/*.log, reports/*.html', allowEmptyArchive: true
            }
        }
        
        success {
            script {
                echo "✅ Pipeline completed successfully!"
                
                // Send success notification
                if (env.BRANCH_NAME == 'main') {
                    emailext (
                        subject: "✅ RAG API Deployed Successfully - ${BUILD_VERSION}",
                        body: """
                        <h2>RAG API Deployment Successful</h2>
                        <p><strong>Version:</strong> ${IMAGE_TAG}</p>
                        <p><strong>Branch:</strong> ${env.BRANCH_NAME}</p>
                        <p><strong>Build:</strong> ${env.BUILD_NUMBER}</p>
                        <p><strong>Commit:</strong> ${env.GIT_COMMIT}</p>
                        <p><strong>Build URL:</strong> <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></p>
                        
                        <h3>Deployment Details:</h3>
                        """,
                        mimeType: 'text/html',
                        to: 'team@company.com'
                    )
                }
            }
        }
        
        failure {
            script {
                echo "❌ Pipeline failed!"
                
                // Send failure notification
                emailext (
                    subject: "❌ RAG API Pipeline Failed - ${BUILD_VERSION}",
                    body: """
                    <h2>RAG API Pipeline Failed</h2>
                    <p><strong>Branch:</strong> ${env.BRANCH_NAME}</p>
                    <p><strong>Build:</strong> ${env.BUILD_NUMBER}</p>
                    <p><strong>Failed Stage:</strong> Check build logs</p>
                    <p><strong>Build URL:</strong> <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></p>
                    
                    <p>Please check the build logs for more details.</p>
                    """,
                    mimeType: 'text/html',
                    to: 'team@company.com'
                )
            }
        }
        
        unstable {
            script {
                echo "⚠️ Pipeline completed with warnings!"
            }
        }
    }
}