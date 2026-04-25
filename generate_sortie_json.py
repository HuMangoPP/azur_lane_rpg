import json

sorties_file_path = "data/sorties.json"

with open(sorties_file_path) as f:
    sortie_data = json.load(f)

while True:
    num_encounters = input("num encounters: ")
    if num_encounters == "exit":
        break
    try:
        num_encounters = int(num_encounters)
    except:
        with open(sorties_file_path, "w+") as f:
            json.dump(sortie_data, f, indent=4)

    encounters = []
    for _ in range(num_encounters):
        front = input("front: ")
        back = input("back: ")

        front = front.split()
        back = back.split()
    
        encounters.append({
            "front": front,
            "back": back
        })

    rewards_string = input("rewards: ")
    rewards_list = rewards_string.split()
    rewards = {}
    for i in range(0, len(rewards_list), 2):
        try:
            rewards[rewards_list[i]] = int(rewards_list[i+1])
        except:
            with open(sorties_file_path, "w+") as f:
                json.dump(sortie_data, f, indent=4)
    sortie_data.append({
        "encounters": encounters,
        "rewards": rewards
    })


with open(sorties_file_path, "w+") as f:
    json.dump(sortie_data, f, indent=4)