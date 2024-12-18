from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required

from init_db import get_db_connection
from models.game import Character, Item, Mage, Monster, Race, Warrior, Tableau

game_bp = Blueprint('game', __name__)


@game_bp.route('/create_character', methods=['GET', 'POST'])
@login_required
def create_character():
    if request.method == 'POST':
        name = request.form.get('name')
        race = request.form.get('race')
        character_class = request.form.get('class')

        # Créer l'instance temporaire du personnage (sans ID)
        if character_class == 'warrior':
            character = Warrior(name=name, race=Race[race.upper()])
        elif character_class == 'mage':
            character = Mage(name=name, race=Race[race.upper()])

        # Sauvegarder dans la base de données
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO characters (name, race, class, health, attack, defense, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (character.name, character.race.name, character.type,
              character.health, character.attack, character.defense,
              current_user.id))

        character_id = cursor.lastrowid
        # Mettre à jour l'ID du personnage
        character.id = character_id

        # Mettre à jour l'active_character_id de l'utilisateur
        cursor.execute('''
            UPDATE user 
            SET active_character_id = ? 
            WHERE user_id = ?
        ''', (character_id, current_user.id))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Personnage créé avec succès!', 'success')
        return redirect(url_for('game.character_profile'))

    return render_template('game/create_character.html')


@game_bp.route('/select_character/<int:character_id>', methods=['POST'])
@login_required
def select_character(character_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Vérifier que le personnage appartient bien à l'utilisateur
    cursor.execute('''
        SELECT * FROM characters 
        WHERE id = ? AND user_id = ?
    ''', (character_id, current_user.id))

    if cursor.fetchone():
        cursor.execute('''
            UPDATE user 
            SET active_character_id = ? 
            WHERE user_id = ?
        ''', (character_id, current_user.id))
        conn.commit()
        flash('Personnage sélectionné avec succès!', 'success')
    else:
        flash('Personnage non trouvé.', 'error')

    cursor.close()
    conn.close()
    return redirect(url_for('game.character_list'))


@game_bp.route('/versus')
@login_required
def versus_mode():
    characters = Character.get_all_by_user(current_user.id)
    return render_template('game/versus.html', characters=characters)


@game_bp.route('/quests')
@login_required
def quest_mode():
    if not current_user.active_character_id:
        flash('Veuillez d\'abord créer ou sélectionner un personnage.', 'warning')
        return redirect(url_for('game.create_character'))

    character = Character.get_by_id(current_user.active_character_id)
    return render_template('game/quests.html', character=character)


def fight_hero_vs_monster(hero, monster):
    """Simulates a fight between a hero and a monster."""
    output = "\n### Quest MODE ###\n"
    print("### Quest MODE ###")

    original_hero_health = hero.health  # Store original hero health points
    output += f"{monster.name} VS {hero.name}\n"
    print(f"{monster.name} VS {hero.name}")

    round = 1  # Reset round for each fight

    # Fight until one of the participants is defeated
    while monster.health > 0 and hero.health > 0:
        output += f"\nRound {round}:\n"
        print(f"Round {round}")

        output += f"# PV de {hero.name} {hero.health}\n"
        print(f"# PV de {hero.name} {hero.health}")

        output += f"# PV de {monster.name} {monster.health}\n"
        print(f"# PV de {monster.name} {monster.health}")

        # Hero attacks monster
        damage_to_monster = hero.attack  # No defense for the monster
        if damage_to_monster < 0:
            damage_to_monster = 0  # No negative damage
        monster.health -= damage_to_monster
        output += f"{hero.name} deals {damage_to_monster} damage to {monster.name}.\n"
        print(f"{hero.name} deals {damage_to_monster} damage to {monster.name}.")

        if monster.health <= 0:
            output += f"\n{hero.name} wins!\n"
            print(f"{hero.name} wins!")
            break  # Monster is defeated

        # Monster retaliates
        damage_to_hero = monster.attack
        if damage_to_hero < 0:
            damage_to_hero = 0  # No negative damage
        hero.health -= damage_to_hero
        output += f"{monster.name} deals {damage_to_hero} damage to {hero.name}.\n"
        print(f"{monster.name} deals {damage_to_hero} damage to {hero.name}.")

        if hero.health <= 0:
            output += f"\n{monster.name} wins!\n"
            print(f"{monster.name} wins!")
            break  # Hero is defeated

        round += 1

    return output


@game_bp.route('/quest/<int:quest_id>', methods=['POST'])
def start_quest(quest_id):
    # Fetch the character and the opponent for the quest
    character = Character.get_by_id(current_user.active_character_id)
    opponent = get_opponent_for_quest(quest_id)

    # Call the quest logic (PvP battle or similar)
    result = fight_hero_vs_monster(character, opponent)

    # Display the result
    return render_template('game/quest_result.html', result=result)


def get_opponent_for_quest(quest_id):
    """Fetches the opponent based on the quest ID."""
    if quest_id == 1:
        return Monster(name="Forest Monster", health=50, attack=10)
    elif quest_id == 2:
        return Monster(name="Cave Troll", health=80, attack=15)
    elif quest_id == 3:
        return Monster(name="Dragon", health=200, attack=40)


@game_bp.route("/fight", methods=["POST"])
@login_required
def fight():
    player1_id = int(request.form.get("player1"))
    player2_id = int(request.form.get("player2"))

    # Retrieve characters based on IDs (replace with DB query)
    characters = Character.get_all_by_user(current_user.id)
    player1 = next((c for c in characters if c.id == player1_id), None)
    player2 = next((c for c in characters if c.id == player2_id), None)

    if not player1 or not player2:
        return "Invalid characters selected", 400

    # Run the fight logic
    result = fight_logic(player1, player2)

    return render_template("game/fight_result.html", result=result)


@game_bp.route('/board_game')
@login_required
def board_game():
    if not current_user.active_character_id:
        flash('Veuillez d\'abord créer ou sélectionner un personnage.', 'warning')
        return redirect(url_for('game.create_character'))

    # Get the active character
    hero = Character.get_by_id(current_user.active_character_id)

    # Create the Tableau game instance
    tableau_game = Tableau(hero)

    # Play the entire game and get the result
    game_result = play_game(tableau_game)

    # You might want to save game results or update character stats here
    # For example:
    if tableau_game.is_completed:
        hero.level =+ 1  # Assuming you have a method to add XP
    elif tableau_game.is_game_over:
        flash('Votre personnage est mort durant le jeu.', 'danger')

    return render_template('game/board_game.html',
                           character=hero,
                           game_result=game_result,
                           tableau_game=tableau_game)


def play_game(Tableau):
    """
    Play the entire tableau game
    """
    output = f"Starting Tableau Game with {Tableau.hero.name}\n"

    while Tableau.current_position < Tableau.length:
        turn_output = Tableau.play_turn()
        output += turn_output

        # Check if hero died during the game
        if Tableau.hero.health <= 0:
            output += f"{Tableau.hero.name} died. Game Over!\n"
            break

    if Tableau.current_position >= Tableau.length:
        output += f"{Tableau.hero.name} completed the tableau and gained experience!\n"

    return output


@game_bp.route('/character_profile')
@login_required
def character_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM characters WHERE user_id = ? ORDER BY id DESC LIMIT 1', (current_user.id,))
    character_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if character_data:
        character = Character(
            id=character_data['id'],
            name=character_data['name'],
            race=Race[character_data['race']],
            character_type=character_data['class'],
            health=character_data['health'],
            attack=character_data['attack'],
            defense=character_data['defense'],
            level=character_data['level']
        )
        return render_template('game/character_profile.html', character=character)

    flash('Aucun personnage trouvé.', 'warning')
    return redirect(url_for('game.create_character'))


@game_bp.route('/characters')
@login_required
def character_list():
    characters = Character.get_all_by_user(current_user.id)
    return render_template('game/character_list.html', characters=characters)


@game_bp.route("/start_battle", methods=["POST"])
def start_battle():
    player1_id = request.json.get("player1")
    player2_id = request.json.get("player2")

    # Simulate game logic
    result = f"Player 1 (Character {player1_id}) battles Player 2 (Character {player2_id})!"
    # Your actual game function would go here instead of this mock result.

    # Return the result
    return jsonify({"result": result})


def fight_logic(player1, player2):
    round = 1
    output = "### PVP MODE ###\n"
    output += f"{player1.name} VS {player2.name}\n\n"
    original_player1_health = player1.health
    original_player2_health = player2.health

    while player1.health > 0 and player2.health > 0:
        output += f"Round {round}:\n"
        output += f"- {player1.name} HP: {player1.health} | {player2.name} HP: {player2.health}\n"

        # Determine initiative: Who attacks first
        if player1.attack > player2.attack:
            output += f"{player1.name} attacks first!\n"
            damage_to_player2 = max(player1.attack - player2.defense, 0)  # Attack - defense, cannot be negative
            player2.health -= damage_to_player2
            output += f"{player1.name} deals {damage_to_player2} damage to {player2.name}\n"
            if player2.health <= 0:
                output += f"{player1.name} wins!\n"
                break
            damage_to_player1 = max(player2.attack - player1.defense, 0)
            player1.health -= damage_to_player1
            output += f"{player2.name} deals {damage_to_player1} damage to {player1.name}\n"
        else:
            output += f"{player2.name} attacks first!\n"
            damage_to_player1 = max(player2.attack - player1.defense, 0)
            player1.health -= damage_to_player1
            output += f"{player2.name} deals {damage_to_player1} damage to {player1.name}\n"
            if player1.health <= 0:
                output += f"{player2.name} wins!\n"
                break
            damage_to_player2 = max(player1.attack - player2.defense, 0)
            player2.health -= damage_to_player2
            output += f"{player1.name} deals {damage_to_player2} damage to {player2.name}\n"

        round += 1

    # Declare the winner
    if player1.health <= 0:
        output += f"\n{player2.name} is victorious!\n"
    elif player2.health <= 0:
        output += f"\n{player1.name} is victorious!\n"

    # Reset player health for future battles (optional)
    player1.health = original_player1_health
    player2.health = original_player2_health

    return output
