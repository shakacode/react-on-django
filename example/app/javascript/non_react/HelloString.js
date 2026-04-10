const HelloString = {
  world() {
    console.warn("server_render_js executed HelloString.world() on the renderer");
    return "<strong data-testid=\"hello-string-output\">Hello from server_render_js</strong>";
  },
};

export default HelloString;
