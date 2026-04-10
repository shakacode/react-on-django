from __future__ import annotations

from django.core.management import call_command


def test_react_install_creates_starter_files(settings, tmp_path):
    settings.BASE_DIR = str(tmp_path)

    call_command("react_install")

    assert (tmp_path / "app/javascript/components/HelloWorld.jsx").exists()
    assert (tmp_path / "app/javascript/components/RscHelloWorld.server.jsx").exists()
    assert (tmp_path / "app/javascript/packs/application.jsx").exists()
    assert (tmp_path / "app/javascript/packs/server-bundle.jsx").exists()
    assert (tmp_path / "app/javascript/packs/rsc-bundle.jsx").exists()


def test_react_generate_creates_component_and_registers_it(settings, tmp_path):
    settings.BASE_DIR = str(tmp_path)
    call_command("react_install")

    call_command("react_generate", "dashboard-card")

    component_path = tmp_path / "app/javascript/components/DashboardCard.jsx"
    application_bundle = (tmp_path / "app/javascript/packs/application.jsx").read_text()
    server_bundle = (tmp_path / "app/javascript/packs/server-bundle.jsx").read_text()

    assert component_path.exists()
    assert 'import DashboardCard from "../components/DashboardCard";' in application_bundle
    assert "RuntimeBridge.register({ HelloWorld, DashboardCard });" in application_bundle
    assert 'import DashboardCard from "../components/DashboardCard";' in server_bundle
    assert "RuntimeBridge.register({ HelloWorld, DashboardCard });" in server_bundle


def test_react_generate_rsc_creates_server_component_and_updates_rsc_bundle(settings, tmp_path):
    settings.BASE_DIR = str(tmp_path)
    call_command("react_install")

    call_command("react_generate", "posts-feed", "--rsc")

    component_path = tmp_path / "app/javascript/components/PostsFeed.server.jsx"
    rsc_bundle = (tmp_path / "app/javascript/packs/rsc-bundle.jsx").read_text()

    assert component_path.exists()
    assert 'import PostsFeed from "../components/PostsFeed.server";' in rsc_bundle
    assert "RuntimeBridge.register({ RscHelloWorld, PostsFeed });" in rsc_bundle
