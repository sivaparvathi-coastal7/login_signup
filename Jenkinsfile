pipeline {
    agent any

    tools {
        // This tells Jenkins to use the Maven version you installed (Check Global Tool Configuration if this name differs)
        maven 'maven' 
    }

    stages {
        stage('Checkout') {
            steps {
                // Gets the latest code
                checkout scm
            }
        }
        
        stage('Build & Test') {
            steps {
                echo '🚀 Starting Real Compilation...'
                // This attempts to compile the Java code. If the code is bad, IT WILL FAIL HERE.
                sh 'mvn clean test' 
            }
        }
    }

    post {
        // This section ONLY runs if the build FAILS (Red)
        failure {
            script {
                echo '❌ Build Failed! Triggering Triage Engine...'
                
                // 1. Get the Build URL so the Engine knows where to look
                def buildUrl = env.BUILD_URL
                def jobName = env.JOB_NAME
                def buildNumber = env.BUILD_NUMBER
                
                // 2. TRIGGER THE TRIAGE ENGINE (Replace the URL below with your actual API endpoint)
                // We send the Build URL to your AI so it can fetch the logs and analyze the error.
                sh """
                   curl -X POST -H "Content-Type: application/json" \
                   -d '{"job": "${jobName}", "build": "${buildNumber}", "url": "${buildUrl}", "status": "FAILURE"}' \
                   http://YOUR_TRIAGE_ENGINE_IP:5000/analyze
                """
            }
        }
        success {
            echo '✅ Build Passed! No Triage needed.'
        }
    }
}
