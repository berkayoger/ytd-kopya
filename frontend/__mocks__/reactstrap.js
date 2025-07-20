module.exports = {
  Button: (props) => {
    return {
      $$typeof: Symbol.for('react.element'),
      type: 'button',
      props
    };
  },
  Input: (props) => {
    return {
      $$typeof: Symbol.for('react.element'),
      type: 'input',
      props
    };
  }
};
