import RuntimeBridge from "react-on-rails-pro";

import HelloWorld from "../components/HelloWorld";
import HelloWorldFromStore from "../components/HelloWorldFromStore";
import MetadataMessage from "../components/MetadataMessage.server";
import RscApp from "../components/RscApp.server";
import HelloString from "../non_react/HelloString";
import createHelloWorldStore from "../stores/helloWorldStore";

RuntimeBridge.register({ HelloWorld, HelloWorldFromStore, MetadataMessage, RscApp, HelloString });
RuntimeBridge.registerStoreGenerators({ helloWorldStore: createHelloWorldStore });
