export default function createHelloWorldStore(props) {
  const state = props ?? {};

  return {
    getState() {
      return state;
    },
    subscribe() {
      return () => {};
    },
    dispatch() {
      return undefined;
    },
  };
}
