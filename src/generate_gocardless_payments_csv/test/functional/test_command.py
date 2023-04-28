import subprocess


def test_command_line_outputs_help():
    response = subprocess.run(
        ["poetry", "run", "generate-gocardless-payments-csv", "--help"],
        check=False,
        capture_output=True
    )
    assert response.returncode == 0
    assert "usage:" in response.stdout.decode()


def test_command_line_fails_with_missing_arguments():
    response = subprocess.run(
        ["poetry", "run", "generate-gocardless-payments-csv"],
        check=False,
        capture_output=True
    )
    assert response.returncode > 0
    assert "the following arguments are required" in response.stderr.decode()
