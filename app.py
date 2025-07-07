from flask import Flask, render_template, request, jsonify
from functions import (
    initialize_conversation,
    initialize_conv_reco,
    get_chat_model_completions,
    moderation_check,
    intent_confirmation_layer,
    compare_laptops_with_user,
    recommendation_validation,
    get_user_requirement_string,
    get_chat_completions_func_calling
)
import openai

with open("OpenAI_API_Key.txt", 'r') as file:
    openai.api_key = file.read().strip()

app = Flask(__name__)

conversation_bot = []
conversation = initialize_conversation()
introduction = get_chat_model_completions(conversation)
conversation_bot.append({'bot': introduction})
top_3_laptops = None

@app.route("/")
def default_func():
    global conversation_bot, conversation, top_3_laptops

    # Only add welcome message if conversation is empty
    if not conversation_bot:
        conversation = initialize_conversation()
        introduction = get_chat_model_completions(conversation)
        conversation_bot.append({'bot': introduction})

    return render_template("conversation_bot.html", name_xyz=conversation_bot)

@app.route("/end_conversation", methods=['POST'])
def end_conv():
    global conversation_bot, conversation, top_3_laptops
    conversation_bot = []
    conversation = initialize_conversation()
    introduction = get_chat_model_completions(conversation)
    conversation_bot.append({'bot': introduction})
    top_3_laptops = None
    return jsonify({"status": "Conversation reset", "bot": introduction})

@app.route("/conversation", methods=['POST'])
def invite():
    global conversation_bot, conversation, top_3_laptops, conversation_reco
    user_input = request.json["user_input_message"]
    moderation = moderation_check(user_input)

    if moderation == 'Flagged':
        return jsonify({"error": "Message flagged, ending conversation."}), 400

    conversation.append({"role": "user", "content": user_input})
    conversation_bot.append({'user': user_input})

    if top_3_laptops is None:
        response_assistant = get_chat_model_completions(conversation)
        moderation = moderation_check(response_assistant)
        if moderation == 'Flagged':
            return jsonify({"error": "Response flagged."}), 400

        confirmation = intent_confirmation_layer(response_assistant)

        if "No" in confirmation:
            conversation.append({"role": "assistant", "content": response_assistant})
            conversation_bot.append({'bot': response_assistant})
        else:
            response = get_user_requirement_string(response_assistant)
            result = get_chat_completions_func_calling(response, True)
            conversation_bot.append({'bot': "Fetching product recommendations..."})

            top_3_laptops = compare_laptops_with_user(result)
            validated_reco = recommendation_validation(top_3_laptops)

            if not validated_reco:
                conversation_bot.append({'bot': "No matching laptops found. Connecting to a human expert."})
            else:
                conversation_reco = initialize_conv_reco(validated_reco)
                recommendation = get_chat_model_completions(conversation_reco)
                conversation_bot.append({'bot': recommendation})

    else:
        conversation_reco.append({"role": "user", "content": user_input})
        response_asst_reco = get_chat_model_completions(conversation_reco)

        moderation = moderation_check(response_asst_reco)
        if moderation == 'Flagged':
            return jsonify({"error": "Response flagged."}), 400

        conversation.append({"role": "assistant", "content": response_asst_reco})
        conversation_bot.append({'bot': response_asst_reco})

    return jsonify({"conversation": conversation_bot})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
