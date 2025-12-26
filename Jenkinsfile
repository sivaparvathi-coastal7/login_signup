post {
        // This 'failure' block ONLY runs if 'mvn test' fails
        failure {
            script {
                echo '❌ Tests Failed! Preparing data for Triage Engine...'

                // 1. Construct the exact JSON Link for this build's test results
                // This link points to the JSON data of the failed tests
                def jsonReportLink = "${env.BUILD_URL}testReport/api/json?pretty=true"
                
                // 2. Prepare the payload to send to your opponent
                // We send them the Build Number and the LINK to the errors
                def payload = """
                {
                    "project": "${env.JOB_NAME}",
                    "build_number": "${env.BUILD_NUMBER}",
                    "status": "FAILURE",
                    "error_data_link": "${jsonReportLink}"
                }
                """

                echo "📤 Sending JSON Link to Opponent: ${jsonReportLink}"

                // 3. Send it! (Replace the URL below with your Opponent's Link)
                sh """
                    curl -X POST -H "Content-Type: application/json" \
                    -d '${payload}' \
                    http://192.168.1.50:5000/webhook
                """
            }
        }
        success {
            echo '✅ Tests Passed. No data sent.'
        }
    }
