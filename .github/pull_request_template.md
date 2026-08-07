<!--
Using AI to help you write code is fine and expected on this project.
Merging code you cannot explain is not. That is what this form is for.
-->

## What does this change?

<!-- One sentence, from the user's point of view. "You can now delete a note." -->

## Explain how it works, in your own words

<!--
The important one. Walk through what actually happens, as if telling a
teammate. Name the files you touched and what each part does.

Not "added a function to handle uploads" — more like: "the route reads the
file, hands the bytes to extract_text, and saves each page as a row. I used a
loop because a PDF has many pages."

If you can't write this section, you're not finished yet. Go and read your own
change until you can. Ask a teammate. Ask an AI to explain it back to you.
-->

## Which part are you least sure about?

<!--
Being honest here is a good thing, not a weakness. It tells the reviewer where
to look and it's how you learn fastest. "I don't really understand why the
await is needed" is a great answer.
-->

## How did you check it works?

<!-- What did you click, type, or run? What did you expect, and what happened? -->

- [ ] I ran it on my own machine and saw it work
- [ ] `ruff check .` and `ruff format .` pass (backend), or `npm run lint` passes (frontend)
- [ ] CI is green

---

<!--
Reviewer: ask one question about the diff. If the author can't answer it, don't
merge yet — send it back so they can go and understand it. That is the whole
point of this project.
-->
