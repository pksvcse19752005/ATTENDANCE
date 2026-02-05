pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                bat 'pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                bat 'pytest'
            }
        }
        stage('Deploy') {
            steps {
                bat 'echo Flask app deployed!'
            }
        }
    }
}
