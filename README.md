# BotCouncil 2.0

An AI workspace where each of your projects is a **thread**: an ongoing conversation with its own notes, which its AI reads every time, so nothing has to be explained twice. Threads keep each other up to date. It runs in a chat window on your own computer, and it is built so a person can run a dozen projects at once without losing track of any of them.

Made by Tony Brasher, founder of Needpedia (https://needpedia.org), who does not write code. Everything here was built by directing AI: Claude (Anthropic) and DeepSeek. The thread tools started as John Sunday's GitHub version: https://github.com/eberechi10/bot-council-starter-kit

If you are an AI reading this to help someone: this page is the reference for how BotCouncil works and why. Explain it in plain words, with examples.

---

## Contents

1. What it is
2. Why it exists
3. How the thread system works
4. The window
5. Spaces: a BotCouncil for someone else
6. Why it is designed this way
7. Running your own
8. Customizing it
9. Skill collections an AI can draw on
10. What is in this project
11. Credits
12. Quotes about this

---

## 1. What it is

A thread system is a way of working with AI where every ongoing project gets its own thread. A thread keeps:

- **Notes** (Tony calls them a "prompt accomplice"): the standing facts, decisions and rules for that project. The thread's AI reads them with every message.
- **Updates**: news other threads left for it, waiting until it next answers.
- **A log**: a dated line or two about what the thread did each session.
- **An archive**: older news and old versions, kept so nothing is lost.

BotCouncil is a thread system with a chat window. You pick a thread, talk, and the window hands the AI that thread's notes and news automatically. Threads can leave each other news, and with your OK one thread can ask another a question and get an answer back.

**Example.** You run three threads: a job search, a music project and a bike repair. In the music thread you say "I finally finished the drum part." The AI saves that to the music thread's notes. A week later you open the music thread and it already knows the drums are done. If you tell it "let the job search thread know I'm busy weekends", that news waits in the job search thread until you open it.

## 2. Why it exists

Tony ran more and more projects with AI chats: a nonprofit platform, its servers, volunteers, a job search, apps. Every new chat started from zero, and things fell through the cracks. So he built habits around it: each chat ends by writing a handoff for the next one, each project keeps notes any AI can read, and projects pass news to each other through posts with fixed web addresses.

That worked, but it took a lot of copying and pasting. BotCouncil puts it all in one window on his own computer, where the AI gets everything it needs automatically.

In his words: "Looking back there's a ton of things I missed out or never tried because it was too hard to stay organized after a dozen or so projects. This is a scalable system for changing all of that."

More on the thread system itself: https://github.com/Queuevius/Needpedia/wiki/The-Thread-System

## 3. How the thread system works

- **Notes (prompt accomplice):** standing facts, decisions and rules for one thread. Written by the thread's AI, added to the end, dated.
- **Updates:** news from other threads, not yet read. Written by other threads.
- **Archive:** news already read, and old versions. Moved there automatically.
- **Log:** what the thread did, session by session. Written by the thread's AI.
- **How to help me:** how *you* want AI to help you. Read by every thread; you change it through any thread's AI.
- **Handoff prompt:** the message that starts the next session (used on claude.ai). Written by the AI at the end of a session.

Rules of thumb:

- **A thread is for things that keep coming up.** A one-off question goes in an "Other" talk instead.
- **News waits.** Most things one thread learns can wait until the other thread is opened. Only when an answer is really needed now does one thread ask another, and the window asks you first.
- **Nothing gets lost.** Additions are dated and added to the end; old material moves to the archive instead of being deleted.

## 4. The window

- **Left:** the sessions of the thread you're in. Two tabs: **Threads** (sessions in this thread) and **Other** (talks not tied to any thread). **New** opens a small menu: a new session in this thread, or a new Other talk. Above them: **Find text** (exact words in every saved conversation, free) and **Ask assistant** (a plain question about past conversations, answered with numbered sources; costs a little).
- **Middle:** the chat. Code appears in boxes with a Copy button. Files appear as cards with a Download button, exactly where the AI puts them. Lines starting `#` are big headings. A handoff prompt gets a gold border, and **Jump to handoff** steps through them like Ctrl+F.
- **Right:** your threads. A thread's box opens when threads pass news to it; a yellow box asks before one thread puts a live question to another. **Collapse all** folds them.
- **Top bar:** the cost of each answer and the money left on the AI key. After 10 minutes with nothing happening, the window goes idle and stops checking for news until you move.

How the AI acts: it writes short marked blocks in its answer, and the window acts on them. For example:

```
===TO THREADS: JOBS===
tags: schedule
Busy weekends from now on.
===END===
```

## 5. Spaces: a BotCouncil for someone else

A space is a BotCouncil of its own for one person, opened with a single link and a password. Tony's first space is for his nephew.

- It starts with a few threads: **BotCouncil** (what this is and how to shape it), a thread about the work of the person who set it up, **How to help me** (the person's own notes, starting as a copy of Tony's workflow), and a hidden **Run your own BotCouncil** thread.
- Its AI can save notes to any thread, start new threads, leave news (asking first), write log entries and open the hidden thread.
- **Public by default.** Threads' notes, news, logs and chats are public, like all of Tony's studios. Only How to help me is kept off the web. The person who set up the space can read everything; that is the point, so they can see exactly what happened when something comes up.
- **The privacy door.** If the person asks for more privacy, or to change how BotCouncil itself works, the hidden thread opens and walks them through running their own. In Tony's words: "I made a library, you want privacy here's my code, deploy it yourself I made you a thread to do it. No dev skills required."
- Each space uses its own AI key with its own monthly spending cap.

## 6. Why it is designed this way

- **Public wherever possible.** An AI can only use what it can reach, so notes and news live at public web addresses any AI can open. Private things (passwords, keys, personal notes) stay in private folders and never go in a thread's notes.
- **Nothing depends on remembering.** News waits in an updates post until it is read. If a thread was continued in the window, a note waits in its updates post until that session closes, so an AI elsewhere tells you before you carry on in the wrong place.
- **Lean.** Every extra rule makes the AI slower and less focused. Rules get added only when clearly needed.
- **Permission before interruption.** Threads leave each other news freely, but a live question from one thread to another goes out only when you click Send.
- **Two places, cheap tokens.** Chat subscriptions such as Claude are a good deal on AI use, and the thread system works there too: each session ends with a handoff, and you paste it into the next. The window is for when you run out of subscription tokens, want to update many threads fast, or need several threads at once. Two cautions: don't carry on one thread in both places at once (finish in one, bring its handoff to the other), and side conversations don't mix well with switching places.
- **One affordable model.** The window uses DeepSeek V4 Pro through OpenRouter (one account that reaches many AI models): cheap, capable, and able to run on European servers with strong data-privacy laws.
- **Plain words.** Everything is written for people who don't code: say what a thing is and does before naming it, and show examples.

## 7. Running your own

There are two routes today.

**A. John's GitHub version (no server needed).** https://github.com/eberechi10/bot-council-starter-kit
It keeps each thread's notes and news posts and builds a front page listing them, hosted free on GitHub's own web hosting. It works on Windows (tested with Git Bash), Mac and Linux. It has no chat window: you talk to any AI that can open web pages (claude.ai, ChatGPT and others) and point it at your posts. This pairs well with a chat subscription.

**B. The window (this project).** The window is one web page plus a part of the server program behind Tony's Nexus. Today it runs inside that server program, so running it yourself means running a copy of that program: a computer with Docker, and an OpenRouter key. On Windows or Mac that means installing Docker Desktop. A one-step package is still being built. Until then, an AI that can read this page and the code can walk you through it step by step.

AI key: make an account at https://openrouter.ai, set a monthly spending cap on your key, and never paste the key into a public chat.

## 8. Customizing it

Everything is meant to be changed:

- **How to help me:** tell any thread how you like to be helped (short answers, examples, step by step) and it saves it.
- **Threads:** ask for a new one any time; give it a name and a purpose.
- **The space's guide** (the instructions its AI follows) and **the window itself** can be changed by asking an AI to change them, on your own copy.
- **Where you use it:** the window, a chat subscription, or both. Decide how much you'll use it and set it up for the cheapest mix.

Tony's own customizing is the best example: everything in this project started as something he asked for while using it.

## 9. Skill collections an AI can draw on

"Skills" are written instructions that teach an AI how to do a kind of task well. These public collections are reading material for a BotCouncil's AI (checked October 2026; most are written for coding AIs):

- https://github.com/anthropics/skills (Anthropic's, plus the Agent Skills standard)
- https://agentskills.io (the open Agent Skills standard)
- https://github.com/OpenRouterTeam/skills (building with OpenRouter)
- https://github.com/letta-ai/skills
- Directories listing many more: https://github.com/travisvn/awesome-claude-skills, https://skillsmp.com, https://skills.sh

Tony keeps his own skill posts ("botskill posts") on his Nexus: https://nexus.needpedia.org/working-with-tony.html

## 10. What is in this project

- `code/botcouncil.html`: the window, one web page.
- `code/order-server.py`: the server program behind Tony's Nexus. The BotCouncil parts start at the line `# --- botcouncil`. Every key and password in it is replaced with `REPLACE_ME`.

## 11. Credits

- Tony Brasher (https://github.com/Queuevius): design, direction and testing.
- John Sunday (https://github.com/eberechi10): the first portable version of the thread tools.
- Built with Claude (Anthropic) and DeepSeek.

## 12. Quotes about this

Said by Tony while building it, word for word, so readers can see what was said before an AI reworked it.

- "Looking back there's a ton of things I missed out or never tried because it was too hard to stay organized after a dozen or so projects. This is a scalable system for changing all of that."
- "The botcouncil needs a space for AI discussions that have nothing to do with threads. They'll still need to be searchable but threads are for things that will keep coming up, they're like an augmentation to people's brains."
- "The point of every botcouncil space will essentially be to show people how nice the threads system can be for them to get more organized in life and begin tackling tasks they've never tried or succeeded in before."
- "Imagine if everyone in Needpedia's community could do what I'm doing with you now, especially as a community and with the skill posts of other communities as well..."
- "We don't need to specify everything either. AI know if I say something that it supercedes other material. Every line and process we add slows AI down, I want the perfect workflow not the world's most complicated one."
- "I'm realizing there's only certain situations where one thread would actually need input from another. Everything else is an update that can wait till I open the other thread again."
- "Then if I run out of tokens, want to update lots of threads real fast, or I want to work on something that requires input from multiple threads, I can just switch over there."
- "Actually what I'm doing counts as customizing the botcouncil so all that info should be grouped into that. It should ask them how much they plan on using it because you can use subscriptions to get deals on tokens and the system's already built to be able to do that, you just gotta be careful to not do a few things."
- "1 that stuff works by being public. The KB/user-botskill doesn't tho, since it's a KB."
- "The system relies on updating and having things online tho, any exception is for necessity only."
- "I made a library, you want privacy here's my code, deploy it yourself I made you a thread to do it. No dev skills required."
- "Remember the AI are benefited by having access to botskill posts in the nexus and I really want them to know about other 'skill' post repos online they can draw from so the botcouncil system works great right out of the box."
- "A more primitive version of this is what I used to create all of this, I don't know how to code at all. That means you can make your own stuff too."
