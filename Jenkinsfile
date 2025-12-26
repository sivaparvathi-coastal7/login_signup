pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code...'
                // Jenkins does this automatically, but this confirms it works
            }
        }
        stage('Build') {
            steps {
                echo 'Building the application...'
                // later you will add: sh 'mvn clean package'
            }
        }
        stage('Test') {
            steps {
                echo 'Running tests...'
                // later you will add: sh 'mvn test'
            }
        }
    }
}
