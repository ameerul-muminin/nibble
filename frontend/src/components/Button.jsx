/**
 * Button — the solid-edge press, in one place.
 *
 * Every button in Nibble has a 3px ink border and a solid 4px shadow directly
 * under it, and drops onto that shadow when pressed. That is the single detail
 * that makes the app feel playful rather than corporate, and a button anywhere
 * that does not do it looks broken. Written 35 times by hand it eventually
 * stops being written the same way, so it is written once here.
 *
 * Props:
 *   variant — 'primary' (lime), 'secondary' (white), 'accent' (indigo), or
 *             'plain' for something that must be a real button for the keyboard
 *             while not looking like one.
 *   type    — defaults to 'button'. Pass 'submit' for the one in a form.
 *   ...rest — everything else, handed straight to the real <button>.
 *
 * ---------------------------------------------------------------------------
 * The `...rest` is not tidiness. It is the whole reason this works.
 *
 * Landing.jsx wraps its buttons in Clerk's <SignInButton mode="modal">. That
 * component does not draw a button of its own — it takes the child it is given,
 * clones it, and attaches its own onClick to the copy. So the onClick that
 * opens the sign-in modal arrives here as a prop, like any other.
 *
 * A component that listed only the props it knew about — variant, type,
 * children — would drop that onClick on the floor. Nothing would break loudly:
 * the button still draws, still presses, still animates, and sign-in silently
 * stops working with no error anywhere to search for.
 *
 * `...rest` is how a component says "I do not know what else you will hand me,
 * and I will pass it on". That is worth understanding before you write the next
 * component, because the failure it prevents is invisible.
 *
 * `type` defaults to 'button' for a smaller version of the same problem: a
 * <button> inside a <form> is a submit button unless you say otherwise, so
 * forgetting it means a button that quietly submits the form it happens to sit
 * in.
 */
export function Button({ variant = 'primary', type = 'button', className = '', ...rest }) {
  const base = variant === 'plain' ? 'btn-plain' : `btn btn--${variant}`
  const classes = className ? `${base} ${className}` : base

  return <button type={type} className={classes} {...rest} />
}
