# tests/test_basic.py
import os

def test_environment_variables():
    """Test that required environment variables are set"""
    assert os.getenv('TESTING') == '1'
    assert os.getenv('FLASK_ENV') == 'testing'
    assert os.getenv('SKIP_HEAVY_IMPORTS') == '1'

def test_basic_import():
    """Test that backend can be imported"""
    try:
        import backend
        assert True
    except ImportError:
        assert False, "Backend import failed"

def test_flask_app_creation():
    """Test Flask app can be created in test mode"""
    try:
        from backend import create_app
        app = create_app()
        assert app is not None
        assert app.config['TESTING'] == True
    except Exception as e:
        assert False, f"App creation failed: {e}"
