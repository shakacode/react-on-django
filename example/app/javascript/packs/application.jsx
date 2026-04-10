import RuntimeBridge from "react-on-rails-pro/client";

import HelloWorld from "../components/HelloWorld";
import HelloWorldFromStore from "../components/HelloWorldFromStore";
import MetadataMessage from "../components/MetadataMessage.client";
import RscApp from "../components/RscApp.client";
import HelloString from "../non_react/HelloString";
import createHelloWorldStore from "../stores/helloWorldStore";
import "../styles/application.css";

RuntimeBridge.register({ HelloWorld, HelloWorldFromStore, MetadataMessage, RscApp, HelloString });
RuntimeBridge.registerStoreGenerators({ helloWorldStore: createHelloWorldStore });
